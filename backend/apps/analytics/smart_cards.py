"""
Cards inteligentes para a Visão Geral.

Cada função analisa os KPIs do tenant e retorna 0 ou 1 card no formato:
    {kind, severity, title, message, action?, metric?}

severity: "info" | "success" | "warning" | "critical"
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from . import kpis, kpis_v2


def _brl(v: float) -> str:
    s = f"{float(v or 0):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    return f"{abs(v):.1f}%".replace(".", ",")


def card_profit_change(tenant_id: int) -> dict | None:
    """Lucro caiu / subiu vs mês anterior."""
    curr = kpis_v2.month_period()
    prev = kpis_v2.previous_month_period()
    np_curr = kpis_v2.net_profit_period(tenant_id, curr)
    np_prev = kpis_v2.net_profit_period(tenant_id, prev)
    if np_prev == 0:
        return None
    change = (np_curr - np_prev) / abs(np_prev) * 100
    if abs(change) < 10:
        return None
    if change < 0:
        return {
            "kind": "profit_drop",
            "severity": "warning" if change > -30 else "critical",
            "title": f"Seu lucro caiu {_pct(change)}",
            "message": (
                f"Lucro líquido em {curr.start.strftime('%m/%Y')} é {_brl(np_curr)} "
                f"contra {_brl(np_prev)} no mês anterior."
            ),
            "action": "/app/dashboards/financeiro",
        }
    return {
        "kind": "profit_surge",
        "severity": "success",
        "title": f"Seu lucro subiu {_pct(change)}",
        "message": (
            f"Excelente! Lucro líquido de {_brl(np_curr)} em {curr.start.strftime('%m/%Y')}."
        ),
        "action": "/app/dashboards/financeiro",
    }


def card_breakeven(tenant_id: int) -> dict | None:
    """Acima/abaixo do ponto de equilíbrio."""
    info = kpis_v2.above_breakeven(tenant_id, kpis_v2.month_period())
    if info["breakeven"] == 0:
        return None
    if info["above"]:
        return {
            "kind": "above_breakeven",
            "severity": "success",
            "title": "Você está acima do ponto de equilíbrio",
            "message": (
                f"Receita {_brl(info['revenue'])} supera o ponto de equilíbrio "
                f"({_brl(info['breakeven'])}). Cada real a mais vira lucro."
            ),
        }
    return {
        "kind": "below_breakeven",
        "severity": "warning",
        "title": "Você está abaixo do ponto de equilíbrio",
        "message": (
            f"Receita de {_brl(info['revenue'])} ainda não cobre o ponto de equilíbrio "
            f"({_brl(info['breakeven'])}). Faltam {_brl(info['breakeven'] - info['revenue'])}."
        ),
        "action": "/app/dashboards/financeiro",
    }


def card_cash_at_risk(tenant_id: int) -> dict | None:
    """Caixa pode ficar negativo nos próximos 30 dias."""
    forecast = kpis_v2.cash_forecast(tenant_id, days=30)
    if not forecast["at_risk"]:
        return None
    return {
        "kind": "cash_at_risk",
        "severity": "critical",
        "title": "Seu caixa pode ficar negativo",
        "message": (
            f"Saldo projetado para os próximos 30 dias: {_brl(forecast['projected_balance'])}. "
            f"Entrada esperada: {_brl(forecast['expected_in'])} · "
            f"Saída esperada: {_brl(forecast['expected_out'])}."
        ),
        "action": "/app/dashboards/financeiro",
    }


def card_expense_surge(tenant_id: int) -> dict | None:
    """Despesas cresceram acima do esperado."""
    curr = kpis_v2.month_period()
    prev = kpis_v2.previous_month_period()
    co_curr = kpis_v2.cash_out_period(tenant_id, curr)
    co_prev = kpis_v2.cash_out_period(tenant_id, prev)
    if co_prev == 0:
        return None
    change = (co_curr - co_prev) / co_prev * 100
    if change < 15:
        return None
    return {
        "kind": "expense_surge",
        "severity": "warning" if change < 40 else "critical",
        "title": f"Despesas cresceram {_pct(change)}",
        "message": (
            f"Em {curr.start.strftime('%m/%Y')} as despesas chegaram a "
            f"{_brl(co_curr)} ({_pct(change)} acima de {co_prev > 0 and prev.start.strftime('%m/%Y') or ''})."
        ),
        "action": "/app/dashboards/financeiro",
    }


def card_low_margin_products(tenant_id: int) -> dict | None:
    """Produtos com margem baixa (preço<=custo) — só faz sentido com price>0."""
    from apps.sync.models import Product

    qs = Product.unsafe_objects.filter(
        tenant_id=tenant_id, is_active=True, price__gt=0,
    )
    bad = qs.filter(price__lte=models_F_cost()).count() if False else 0
    # Inline simples (sem F field comparison): conta manualmente
    count_low = 0
    for p in qs[:200]:
        if p.cost and p.price <= p.cost:
            count_low += 1
    if count_low == 0:
        return None
    return {
        "kind": "low_margin_products",
        "severity": "warning",
        "title": f"{count_low} produto(s) com margem baixa",
        "message": (
            "Produtos com preço de venda menor ou igual ao custo médio. "
            "Revise para não vender no prejuízo."
        ),
        "action": "/app/products",
    }


def models_F_cost():  # type: ignore[no-untyped-def]
    """Stub para futura comparação Price <= F('cost') via QuerySet annotation."""
    from django.db.models import F
    return F("cost")


def card_revenue_decel(tenant_id: int) -> dict | None:
    """Vendas/recebimentos desaceleraram."""
    curr = kpis_v2.month_period()
    prev = kpis_v2.previous_month_period()
    ci_curr = kpis_v2.cash_in_period(tenant_id, curr)
    ci_prev = kpis_v2.cash_in_period(tenant_id, prev)
    if ci_prev == 0:
        return None
    change = (ci_curr - ci_prev) / ci_prev * 100
    if change > -10:
        return None
    return {
        "kind": "revenue_decel",
        "severity": "warning" if change > -25 else "critical",
        "title": f"Vendas desaceleraram {_pct(change)}",
        "message": (
            f"Recebimentos em {curr.start.strftime('%m/%Y')}: {_brl(ci_curr)} "
            f"(contra {_brl(ci_prev)} no mês anterior)."
        ),
        "action": "/app/dashboards/comercial",
    }


def card_overdue_high(tenant_id: int) -> dict | None:
    """Inadimplência crítica."""
    rate = kpis.overdue_rate(tenant_id)
    if rate < 10:
        return None
    return {
        "kind": "overdue_high",
        "severity": "warning" if rate < 20 else "critical",
        "title": f"Inadimplência em {_pct(rate)}",
        "message": "Acima do limite saudável (10%). Reforce a régua de cobrança.",
        "action": "/app/dashboards/financeiro",
    }


def card_supplier_concentration(tenant_id: int) -> dict | None:
    """Fornecedor único concentrando muito."""
    period = kpis_v2.month_period()
    rows = kpis.top_financial_customers(
        tenant_id, period, direction="payable", limit=1,
    )
    if not rows:
        return None
    top = rows[0]
    total = kpis_v2.cash_out_period(tenant_id, period)
    if total <= 0:
        return None
    share = top["total"] / total * 100
    if share < 35:
        return None
    return {
        "kind": "supplier_concentration",
        "severity": "warning",
        "title": f"\"{top['name']}\" = {_pct(share)} dos pagamentos",
        "message": (
            f"{_brl(top['total'])} pagos a um único fornecedor este mês — "
            f"considere diversificar."
        ),
        "action": "/app/customers?type=supplier",
    }


# ---------------------------------------------------------------------------
ALL_GENERATORS = [
    card_cash_at_risk,         # crítico vem primeiro
    card_overdue_high,
    card_revenue_decel,
    card_expense_surge,
    card_profit_change,
    card_breakeven,
    card_supplier_concentration,
    card_low_margin_products,
]


def build_smart_cards(tenant_id: int, *, max_cards: int = 6) -> list[dict[str, Any]]:
    """Roda todos os geradores e devolve até `max_cards`, priorizando severidade."""
    out: list[dict] = []
    for gen in ALL_GENERATORS:
        try:
            card = gen(tenant_id)
            if card:
                out.append(card)
        except Exception:  # noqa: BLE001
            continue
    # ordenar por severidade
    severity_order = {"critical": 0, "warning": 1, "success": 2, "info": 3}
    out.sort(key=lambda c: severity_order.get(c.get("severity", "info"), 4))
    return out[:max_cards]
