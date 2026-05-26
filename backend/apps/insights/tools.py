"""
Catálogo de ferramentas (function calling) que o agente IA pode chamar.

Cada ferramenta:
- Tem um schema JSON (OpenAI tool spec)
- Tem um handler Python que executa a operação
- Recebe `tenant_id` como primeiro argumento (injetado pelo agent)
- Retorna dict serializável (JSON-friendly)

Filosofia:
- Ferramentas são granulares — uma pergunta complexa vira várias chamadas
- LLM decide quando/quais chamar (não temos mais intent-based hardcoded)
- Resultados retornam números formatados (mas LLM faz a narração)
- Todas as queries respeitam isolamento por tenant
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, time
from decimal import Decimal
from typing import Any, Callable

from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Max,
    Q,
    Sum,
)
from django.utils import timezone


def _f(v) -> float:  # type: ignore[no-untyped-def]
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def _period_from_days(days: int):  # type: ignore[no-untyped-def]
    from apps.analytics.periods import Period

    today = timezone.now().date()
    return Period(start=today - timedelta(days=days), end=today)


# ===========================================================================
# Handlers
# ===========================================================================
def get_entity_counts(tenant_id: int) -> dict[str, Any]:
    """Retorna contagens básicas de entidades sincronizadas."""
    from apps.sync.models import (
        Category,
        Customer,
        FinancialEntry,
        Product,
        Sale,
        Salesperson,
    )

    stock_agg = Product.unsafe_objects.filter(
        tenant_id=tenant_id, stock_balance__gt=0, cost__gt=0,
    ).aggregate(
        qty=Sum("stock_balance"),
        value=Sum(
            ExpressionWrapper(
                F("stock_balance") * F("cost"),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            ),
        ),
    )
    return {
        "products_total": Product.unsafe_objects.filter(tenant_id=tenant_id).count(),
        "products_active": Product.unsafe_objects.filter(tenant_id=tenant_id, is_active=True).count(),
        "products_in_stock": Product.unsafe_objects.filter(tenant_id=tenant_id, stock_balance__gt=0).count(),
        "stock_total_qty": _f(stock_agg.get("qty")),
        "stock_total_value_brl": _f(stock_agg.get("value")),
        "customers_total": Customer.unsafe_objects.filter(tenant_id=tenant_id).count(),
        "customers_active": Customer.unsafe_objects.filter(tenant_id=tenant_id, is_active=True).count(),
        "categories": Category.unsafe_objects.filter(tenant_id=tenant_id).count(),
        "salespeople": Salesperson.unsafe_objects.filter(tenant_id=tenant_id).count(),
        "sales_total": Sale.unsafe_objects.filter(tenant_id=tenant_id).count(),
        "financial_entries_total": FinancialEntry.unsafe_objects.filter(tenant_id=tenant_id).count(),
        "financial_receivable_paid": FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id, direction="receivable", status="paid",
        ).count(),
        "financial_payable_paid": FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id, direction="payable", status="paid",
        ).count(),
        "financial_open_receivable": FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id, direction="receivable", status__in=["pending", "overdue"],
        ).count(),
        "financial_open_payable": FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id, direction="payable", status__in=["pending", "overdue"],
        ).count(),
    }


def get_kpis_period(tenant_id: int, days: int = 30) -> dict[str, Any]:
    """KPIs financeiros do período (cash_in, cash_out, lucro, margem, EBITDA, breakeven)."""
    from apps.analytics import kpis_v2 as kv2

    period = _period_from_days(days)
    ci = kv2.cash_in_period(tenant_id, period)
    co = kv2.cash_out_period(tenant_id, period)
    return {
        "period_days": days,
        "period_start": period.start.isoformat(),
        "period_end": period.end.isoformat(),
        "cash_in_brl": ci,
        "cash_out_brl": co,
        "net_profit_brl": ci - co,
        "net_margin_pct": kv2.net_margin_pct(tenant_id, period),
        "ebitda_brl": kv2.ebitda(tenant_id, period),
        "contribution_margin_pct": kv2.contribution_margin_pct(tenant_id, period),
        "expense_breakdown": kv2.expense_breakdown(tenant_id, period),
        "breakeven": kv2.above_breakeven(tenant_id, period),
        "roi_operational_pct": kv2.roi_operational(tenant_id, period),
    }


def get_kpis_for_period(
    tenant_id: int, start_date: str, end_date: str,
) -> dict[str, Any]:
    """KPIs para um intervalo de datas arbitrário (ISO 8601 YYYY-MM-DD).

    Use SEMPRE que o usuário perguntar sobre um mês/trimestre/ano específico
    do passado, em vez de get_kpis_period (que só aceita N dias atrás).
    Ex: 'dezembro 2025' → start_date=2025-12-01 end_date=2025-12-31.
    """
    from datetime import date

    from apps.analytics import kpis_v2 as kv2
    from apps.analytics.periods import Period

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except (ValueError, TypeError):
        return {
            "error": (
                f"Datas inválidas: start_date={start_date!r} end_date={end_date!r}. "
                "Use formato ISO 8601: YYYY-MM-DD"
            )
        }
    if end < start:
        return {"error": "end_date deve ser >= start_date"}

    period = Period(start=start, end=end)
    ci = kv2.cash_in_period(tenant_id, period)
    co = kv2.cash_out_period(tenant_id, period)
    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "period_days": (end - start).days + 1,
        "cash_in_brl": ci,
        "cash_out_brl": co,
        "net_profit_brl": ci - co,
        "net_margin_pct": kv2.net_margin_pct(tenant_id, period),
        "ebitda_brl": kv2.ebitda(tenant_id, period),
        "expense_breakdown": kv2.expense_breakdown(tenant_id, period),
        "has_data": ci > 0 or co > 0,
    }


def get_cash_balance(tenant_id: int) -> dict[str, Any]:
    """Saldo de caixa acumulado + capital de giro."""
    from apps.analytics import kpis_v2 as kv2

    return {
        "cash_balance_brl": kv2.cash_balance(tenant_id),
        "burn_rate_monthly_brl": kv2.burn_rate(tenant_id, months=3),
        "working_capital": kv2.working_capital(tenant_id),
    }


def get_forecast(tenant_id: int, kind: str = "revenue", days_ahead: int = 30) -> dict[str, Any]:
    """Previsão. kind = 'revenue' | 'expense' | 'cash'."""
    from apps.analytics import kpis_v2 as kv2

    if kind == "revenue":
        return kv2.revenue_forecast(tenant_id, days_ahead=days_ahead)
    if kind == "expense":
        return kv2.expense_forecast(tenant_id, days_ahead=days_ahead)
    if kind == "cash":
        return kv2.cash_forecast(tenant_id, days=days_ahead)
    return {"error": f"kind inválido: {kind}. Use revenue/expense/cash."}


def get_top_categories(tenant_id: int, direction: str = "payable", days: int = 30, limit: int = 10) -> dict[str, Any]:
    """Top categorias por valor pago. direction = 'receivable' (receitas) | 'payable' (despesas)."""
    from apps.analytics import kpis as kv1

    period = _period_from_days(days)
    rows = kv1.top_categories(tenant_id, period, direction=direction, limit=limit)
    return {
        "direction": direction,
        "period_days": days,
        "total_brl": sum(r["total"] for r in rows),
        "rows": rows,
    }


def get_top_financial_customers(tenant_id: int, direction: str = "receivable", days: int = 30, limit: int = 10) -> dict[str, Any]:
    """Top clientes (receivable) ou fornecedores (payable) por valor."""
    from apps.analytics import kpis as kv1

    period = _period_from_days(days)
    rows = kv1.top_financial_customers(tenant_id, period, direction=direction, limit=limit)
    return {
        "direction": direction,
        "period_days": days,
        "total_brl": sum(r["total"] for r in rows),
        "rows": rows,
    }


def get_overdue_summary(tenant_id: int) -> dict[str, Any]:
    """Resumo de inadimplência (recebíveis e pagáveis vencidos)."""
    from apps.analytics import kpis as kv1

    return {
        "overdue_rate_pct": kv1.overdue_rate(tenant_id),
        "overdue_receivables": kv1.overdue_receivables_summary(tenant_id),
        "overdue_payables": kv1.overdue_payables_summary(tenant_id),
    }


def get_upcoming(tenant_id: int, direction: str = "payable", days: int = 30) -> dict[str, Any]:
    """Lançamentos com vencimento nos próximos N dias."""
    from apps.analytics import kpis as kv1

    if direction == "receivable":
        return kv1.upcoming_receivables(tenant_id, days=days)
    return kv1.upcoming_payables(tenant_id, days=days)


def get_cashflow_monthly(tenant_id: int, months: int = 12) -> dict[str, Any]:
    """Fluxo de caixa mensal (entradas, saídas, líquido)."""
    from apps.analytics import kpis as kv1

    period = _period_from_days(months * 30)
    rows = kv1.cashflow_by_month(tenant_id, period)
    return {
        "months": months,
        "rows": rows,
        "total_in_brl": sum(m["in"] for m in rows),
        "total_out_brl": sum(m["out"] for m in rows),
        "total_net_brl": sum(m["net"] for m in rows),
    }


def get_dre(tenant_id: int, days: int = 30) -> dict[str, Any]:
    """DRE estruturado (receitas, custos fixos, variáveis, margem, lucro)."""
    from apps.analytics import kpis_v2 as kv2

    return kv2.dre_structured(tenant_id, _period_from_days(days))


def get_health_score(tenant_id: int) -> dict[str, Any]:
    """Score de saúde financeira 0-100 + componentes."""
    from apps.analytics import kpis_v2 as kv2

    return kv2.financial_health_score(tenant_id)


def get_rfv_segments(tenant_id: int) -> dict[str, Any]:
    """Segmentação RFV de clientes (Champions, Loyal, At Risk, Lost, New, High Value)."""
    from apps.analytics import kpis_v2 as kv2

    return kv2.rfv_segments(tenant_id)


def get_customers_at_risk(tenant_id: int, inactive_days: int = 60) -> dict[str, Any]:
    """Clientes recorrentes inativos há N+ dias."""
    from apps.analytics import kpis_v2 as kv2

    rows = kv2.customer_at_risk(tenant_id, inactive_days=inactive_days)
    return {
        "inactive_days_threshold": inactive_days,
        "count": len(rows),
        "total_historical_brl": sum(r["total_purchased"] for r in rows),
        "customers": rows,
    }


def get_ltv(tenant_id: int, months_back: int = 12) -> dict[str, Any]:
    """LTV médio + clientes únicos."""
    from apps.analytics import kpis_v2 as kv2

    return kv2.ltv_estimate(tenant_id, months_back=months_back)


def get_repurchase_rate(tenant_id: int, window_days: int = 90) -> dict[str, Any]:
    """Taxa de recompra de clientes."""
    from apps.analytics import kpis_v2 as kv2

    return kv2.repurchase_rate(tenant_id, window_days=window_days)


def get_abc_curve(tenant_id: int, by: str = "stock_value") -> dict[str, Any]:
    """Curva ABC de produtos. by = 'stock_value' (saldo×custo) | 'sales' (receita)."""
    from apps.analytics import kpis_v2 as kv2

    return kv2.abc_curve(tenant_id, by=by)


def get_stagnant_products(tenant_id: int, min_stock: int = 1) -> dict[str, Any]:
    """Produtos com estoque mas sem vendas registradas."""
    from apps.analytics import kpis_v2 as kv2

    rows = kv2.stagnant_products(tenant_id, min_stock=min_stock)
    return {
        "count": len(rows),
        "total_stuck_value_brl": sum(r["stuck_value"] for r in rows),
        "products": rows,
    }


def get_reorder_suggestions(tenant_id: int, lookback_days: int = 180, target_coverage_days: int = 30) -> dict[str, Any]:
    """Sugestões de recompra baseado em velocidade de saída."""
    from apps.analytics import kpis_v2 as kv2

    return kv2.reorder_suggestions(
        tenant_id, lookback_days=lookback_days, target_coverage_days=target_coverage_days,
    )


def search_customers(tenant_id: int, query: str = "", limit: int = 20) -> dict[str, Any]:
    """Busca clientes por nome. Retorna até `limit` resultados com totalizadores."""
    from apps.sync.models import Customer, FinancialEntry

    qs = Customer.unsafe_objects.filter(tenant_id=tenant_id)
    if query:
        qs = qs.filter(name__icontains=query)
    recv = Q(financial_entries__direction="receivable")
    pay = Q(financial_entries__direction="payable")
    qs = qs.annotate(
        recv_total=Sum("financial_entries__amount", filter=recv),
        pay_total=Sum("financial_entries__amount", filter=pay),
        recv_count=Count("financial_entries", filter=recv),
        pay_count=Count("financial_entries", filter=pay),
        last_txn=Max("financial_entries__paid_at"),
    ).order_by(F("recv_total").desc(nulls_last=True))[:limit]

    rows = [
        {
            "id": c.id,
            "name": c.name,
            "document": c.document or "",
            "email": c.email or "",
            "received_brl": _f(c.recv_total),
            "paid_brl": _f(c.pay_total),
            "received_count": c.recv_count or 0,
            "paid_count": c.pay_count or 0,
            "last_transaction": c.last_txn.isoformat() if c.last_txn else None,
            "is_active": c.is_active,
        }
        for c in qs
    ]
    return {"query": query, "count": len(rows), "rows": rows}


def search_products(tenant_id: int, query: str = "", limit: int = 20) -> dict[str, Any]:
    """Busca produtos por nome ou SKU."""
    from apps.sync.models import Product

    qs = Product.unsafe_objects.filter(tenant_id=tenant_id)
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    qs = qs.order_by(F("stock_balance").desc(nulls_last=True))[:limit]
    rows = [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "price_brl": _f(p.price),
            "cost_brl": _f(p.cost),
            "stock": _f(p.stock_balance),
            "stock_value_brl": _f(p.stock_balance * p.cost),
            "is_active": p.is_active,
            "margin_pct": (
                float((p.price - p.cost) / p.price * 100)
                if p.price and p.cost is not None else 0.0
            ),
        }
        for p in qs
    ]
    return {"query": query, "count": len(rows), "rows": rows}


def search_financial_entries(
    tenant_id: int,
    direction: str = "any",
    status: str = "any",
    days_back: int = 30,
    limit: int = 20,
    min_amount: float = 0,
) -> dict[str, Any]:
    """
    Busca lançamentos financeiros com filtros.
    direction: 'receivable' | 'payable' | 'any'
    status: 'paid' | 'pending' | 'overdue' | 'any'
    """
    from apps.sync.models import FinancialEntry

    qs = FinancialEntry.unsafe_objects.filter(tenant_id=tenant_id)
    if direction in ("receivable", "payable"):
        qs = qs.filter(direction=direction)
    if status in ("paid", "pending", "overdue", "canceled"):
        qs = qs.filter(status=status)
    if days_back > 0:
        cutoff = timezone.now().date() - timedelta(days=days_back)
        qs = qs.filter(Q(paid_at__gte=cutoff) | Q(due_date__gte=cutoff))
    if min_amount > 0:
        qs = qs.filter(amount__gte=min_amount)

    qs = qs.select_related("category", "customer").order_by("-amount")[:limit]
    rows = [
        {
            "id": fe.id,
            "direction": fe.direction,
            "status": fe.status,
            "amount_brl": _f(fe.amount),
            "description": fe.description[:100] if fe.description else "",
            "due_date": fe.due_date.isoformat() if fe.due_date else None,
            "paid_at": fe.paid_at.isoformat() if fe.paid_at else None,
            "category": fe.category.name if fe.category else None,
            "customer": fe.customer.name if fe.customer else None,
        }
        for fe in qs
    ]
    return {
        "filter": {"direction": direction, "status": status, "days_back": days_back, "min_amount": min_amount},
        "count": len(rows),
        "rows": rows,
    }


def search_sales(tenant_id: int, days_back: int = 30, limit: int = 20) -> dict[str, Any]:
    """Lista vendas formais (módulo Sale do Conta Azul)."""
    from apps.sync.models import Sale

    cutoff = timezone.make_aware(datetime.combine(
        timezone.now().date() - timedelta(days=days_back), time.min,
    ))
    qs = (
        Sale.unsafe_objects.filter(tenant_id=tenant_id, issued_at__gte=cutoff)
        .select_related("customer", "salesperson")
        .order_by("-issued_at")[:limit]
    )
    rows = [
        {
            "id": s.id,
            "number": s.number,
            "status": s.status,
            "total_brl": _f(s.total),
            "issued_at": s.issued_at.isoformat() if s.issued_at else None,
            "customer": s.customer.name if s.customer else None,
            "salesperson": s.salesperson.name if s.salesperson else None,
        }
        for s in qs
    ]
    return {
        "filter": {"days_back": days_back},
        "count": len(rows),
        "total_value_brl": sum(_f(s["total_brl"]) for s in rows),
        "rows": rows,
    }


# ===========================================================================
# Schemas OpenAI (tool calling format)
# ===========================================================================
# Cada tupla é: (handler, OpenAI tool schema)
TOOLS: dict[str, tuple[Callable, dict[str, Any]]] = {
    "get_entity_counts": (
        get_entity_counts,
        {
            "type": "function",
            "function": {
                "name": "get_entity_counts",
                "description": (
                    "Retorna contagens totais de cada tipo de entidade na base do "
                    "tenant: produtos, clientes, vendas, lançamentos financeiros, "
                    "categorias, vendedores. Use quando o usuário perguntar "
                    "'quantos X tenho' ou querer um inventário."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ),
    "get_kpis_period": (
        get_kpis_period,
        {
            "type": "function",
            "function": {
                "name": "get_kpis_period",
                "description": (
                    "KPIs HISTÓRICOS dos ÚLTIMOS N DIAS (terminando hoje): cash_in, "
                    "cash_out, lucro líquido, margem, EBITDA, ponto de equilíbrio. "
                    "Use APENAS para 'últimos X dias' (ex: 'últimos 30/90/365 dias'). "
                    "Para mês/trimestre/ano específico (ex: 'dezembro/2025', 'Q3 2024'), "
                    "use get_kpis_for_period com datas exatas. Para previsão futura, "
                    "use get_forecast."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Tamanho do período em dias terminando hoje (30, 90, 365)",
                            "default": 30,
                        },
                    },
                },
            },
        },
    ),
    "get_kpis_for_period": (
        get_kpis_for_period,
        {
            "type": "function",
            "function": {
                "name": "get_kpis_for_period",
                "description": (
                    "KPIs HISTÓRICOS de um INTERVALO DE DATAS específico. Use para "
                    "qualquer pergunta que mencione mês/trimestre/semestre/ano "
                    "explícito (ex: 'dezembro de 2025', 'Q3 2024', 'segundo semestre'). "
                    "Retorna also 'has_data: false' quando não há dados no período "
                    "— NUNCA invente valores se has_data=false."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Data início em ISO 8601 (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Data fim em ISO 8601 (YYYY-MM-DD)",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            },
        },
    ),
    "get_cash_balance": (
        get_cash_balance,
        {
            "type": "function",
            "function": {
                "name": "get_cash_balance",
                "description": (
                    "Saldo de caixa acumulado HOJE + burn rate mensal + "
                    "capital de giro (recebíveis abertos vs pagáveis abertos). "
                    "Use para perguntas sobre saúde de caixa atual."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ),
    "get_forecast": (
        get_forecast,
        {
            "type": "function",
            "function": {
                "name": "get_forecast",
                "description": (
                    "Previsão futura. 'revenue' usa regressão linear sobre últimos "
                    "6 meses (com nível de confiança); 'expense' usa média móvel; "
                    "'cash' projeta saldo baseado em recebíveis/pagáveis em aberto."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "kind": {
                            "type": "string",
                            "enum": ["revenue", "expense", "cash"],
                            "description": "Tipo de previsão",
                        },
                        "days_ahead": {
                            "type": "integer",
                            "description": "Horizonte (dias). Padrão 30.",
                            "default": 30,
                        },
                    },
                    "required": ["kind"],
                },
            },
        },
    ),
    "get_top_categories": (
        get_top_categories,
        {
            "type": "function",
            "function": {
                "name": "get_top_categories",
                "description": (
                    "Top N categorias por valor no período. direction='receivable' "
                    "= categorias de RECEITA. direction='payable' = categorias de "
                    "DESPESA. Use pra 'onde entra/sai dinheiro'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["receivable", "payable"]},
                        "days": {"type": "integer", "default": 30},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["direction"],
                },
            },
        },
    ),
    "get_top_financial_customers": (
        get_top_financial_customers,
        {
            "type": "function",
            "function": {
                "name": "get_top_financial_customers",
                "description": (
                    "Top N clientes (direction='receivable') ou fornecedores "
                    "(direction='payable') por valor de transação no período."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["receivable", "payable"]},
                        "days": {"type": "integer", "default": 30},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["direction"],
                },
            },
        },
    ),
    "get_overdue_summary": (
        get_overdue_summary,
        {
            "type": "function",
            "function": {
                "name": "get_overdue_summary",
                "description": "Inadimplência atual: % e valores vencidos (recebíveis e pagáveis).",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ),
    "get_upcoming": (
        get_upcoming,
        {
            "type": "function",
            "function": {
                "name": "get_upcoming",
                "description": (
                    "Lançamentos com vencimento nos próximos N dias. Use pra "
                    "'a pagar/receber próximos 30/60/90 dias'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["receivable", "payable"]},
                        "days": {"type": "integer", "default": 30},
                    },
                    "required": ["direction"],
                },
            },
        },
    ),
    "get_cashflow_monthly": (
        get_cashflow_monthly,
        {
            "type": "function",
            "function": {
                "name": "get_cashflow_monthly",
                "description": "Fluxo de caixa mês a mês: entradas, saídas, líquido. Use pra ver tendência.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "months": {"type": "integer", "default": 12},
                    },
                },
            },
        },
    ),
    "get_dre": (
        get_dre,
        {
            "type": "function",
            "function": {
                "name": "get_dre",
                "description": (
                    "DRE estruturado por categoria: receitas, custos variáveis, "
                    "margem de contribuição, custos fixos, lucro líquido, EBITDA. "
                    "Use pra análise de demonstrativo de resultado."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"days": {"type": "integer", "default": 30}},
                },
            },
        },
    ),
    "get_health_score": (
        get_health_score,
        {
            "type": "function",
            "function": {
                "name": "get_health_score",
                "description": (
                    "Score de saúde financeira (0-100) com 4 componentes: margem, "
                    "caixa, inadimplência, concentração de fornecedor."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ),
    "get_rfv_segments": (
        get_rfv_segments,
        {
            "type": "function",
            "function": {
                "name": "get_rfv_segments",
                "description": (
                    "Segmentação RFV (Recência, Frequência, Valor) dos clientes em "
                    "6 grupos: champions, loyal, high_value, new, at_risk, lost. "
                    "Retorna até 20 clientes top por segmento."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ),
    "get_customers_at_risk": (
        get_customers_at_risk,
        {
            "type": "function",
            "function": {
                "name": "get_customers_at_risk",
                "description": (
                    "Clientes que TINHAM compras recorrentes mas pararam há mais "
                    "de N dias. Inclui histórico de valor e dias inativo."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "inactive_days": {"type": "integer", "default": 60},
                    },
                },
            },
        },
    ),
    "get_ltv": (
        get_ltv,
        {
            "type": "function",
            "function": {
                "name": "get_ltv",
                "description": "LTV (lifetime value) médio dos clientes únicos nos últimos N meses.",
                "parameters": {
                    "type": "object",
                    "properties": {"months_back": {"type": "integer", "default": 12}},
                },
            },
        },
    ),
    "get_repurchase_rate": (
        get_repurchase_rate,
        {
            "type": "function",
            "function": {
                "name": "get_repurchase_rate",
                "description": "Taxa de recompra: % de clientes que voltaram a comprar na janela.",
                "parameters": {
                    "type": "object",
                    "properties": {"window_days": {"type": "integer", "default": 90}},
                },
            },
        },
    ),
    "get_abc_curve": (
        get_abc_curve,
        {
            "type": "function",
            "function": {
                "name": "get_abc_curve",
                "description": (
                    "Curva ABC de produtos: classifica em A (80% valor), B (15%), "
                    "C (5%). 'stock_value' usa saldo×custo; 'sales' usa receita."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "by": {"type": "string", "enum": ["stock_value", "sales"]},
                    },
                },
            },
        },
    ),
    "get_stagnant_products": (
        get_stagnant_products,
        {
            "type": "function",
            "function": {
                "name": "get_stagnant_products",
                "description": "Produtos com estoque mas SEM vendas registradas (capital travado).",
                "parameters": {
                    "type": "object",
                    "properties": {"min_stock": {"type": "integer", "default": 1}},
                },
            },
        },
    ),
    "get_reorder_suggestions": (
        get_reorder_suggestions,
        {
            "type": "function",
            "function": {
                "name": "get_reorder_suggestions",
                "description": (
                    "Sugestões de recompra: produtos com cobertura de estoque < N "
                    "dias, baseado em velocidade de saída histórica."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lookback_days": {"type": "integer", "default": 180},
                        "target_coverage_days": {"type": "integer", "default": 30},
                    },
                },
            },
        },
    ),
    "search_customers": (
        search_customers,
        {
            "type": "function",
            "function": {
                "name": "search_customers",
                "description": "Busca clientes por nome (case-insensitive). Retorna até `limit` com totais.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
        },
    ),
    "search_products": (
        search_products,
        {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "Busca produtos por nome ou SKU.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
        },
    ),
    "search_financial_entries": (
        search_financial_entries,
        {
            "type": "function",
            "function": {
                "name": "search_financial_entries",
                "description": (
                    "Busca lançamentos financeiros com filtros. Use pra responder "
                    "'me mostre as faturas atrasadas', 'maiores despesas pagas', etc."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["receivable", "payable", "any"]},
                        "status": {"type": "string", "enum": ["paid", "pending", "overdue", "canceled", "any"]},
                        "days_back": {"type": "integer", "default": 30},
                        "min_amount": {"type": "number", "default": 0},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
        },
    ),
    "search_sales": (
        search_sales,
        {
            "type": "function",
            "function": {
                "name": "search_sales",
                "description": "Lista vendas formais (módulo Sale). Use para 'minhas últimas vendas' etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days_back": {"type": "integer", "default": 30},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
        },
    ),
}


def get_openai_tools_schema() -> list[dict]:
    """Retorna lista de tools no formato esperado pela OpenAI API."""
    return [schema for _, schema in TOOLS.values()]


def execute_tool(tenant_id: int, name: str, args: dict) -> dict[str, Any]:
    """Executa uma ferramenta pelo nome. Captura erros e retorna dict-friendly."""
    if name not in TOOLS:
        return {"error": f"Ferramenta '{name}' não existe."}
    handler, _ = TOOLS[name]
    try:
        return handler(tenant_id, **args)
    except TypeError as e:
        return {"error": f"Argumentos inválidos para {name}: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{name} falhou: {type(e).__name__}: {e}"}
