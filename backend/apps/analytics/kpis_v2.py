"""
KPIs v2 — financeiros e analíticos avançados para a nova arquitetura BI AZUL.

Todos os cálculos derivam de `FinancialEntry` (já que `Sale` é opcional/raro
em tenants de varejo). KPIs que dependem de venda formal são marcados com
`requires_sales=True` no retorno e simplesmente vêm zerados quando não há
dados — a UI sabe esconder.

Filosofia:
- Funções puras: `(tenant_id, period) -> número`
- Comparativos sempre versus o período anterior de mesma duração
- Score de saúde 0-100 derivado de pesos sobre 4 dimensões
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, F, Max, Sum
from django.utils import timezone

from apps.sync.models import (
    Customer,
    FinancialEntry,
    Product,
    Sale,
    SaleItem,
)

from .periods import Period, month_buckets


# ---------------------------------------------------------------------------
def _f(v) -> float:  # type: ignore[no-untyped-def]
    if v is None:
        return 0.0
    return float(v)


def _pct(curr: float, prev: float) -> float | None:
    if not prev:
        return None
    return (curr - prev) / prev * 100


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _aware(d: date, *, end: bool = False) -> datetime:
    return timezone.make_aware(datetime.combine(d, time.max if end else time.min))


def month_period(ref: date | None = None) -> Period:
    """Período do mês corrente (ou do ref)."""
    ref = ref or timezone.now().date()
    start = ref.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
    return Period(start=start, end=end)


def previous_month_period(ref: date | None = None) -> Period:
    """Período do mês anterior."""
    p = month_period(ref)
    prev_end = p.start - timedelta(days=1)
    return month_period(prev_end)


# ===========================================================================
# Core financeiro
# ===========================================================================
def cash_in_period(tenant_id: int, period: Period) -> float:
    v = (
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
        )
        .aggregate(t=Sum("amount"))["t"]
    )
    return _f(v)


def cash_out_period(tenant_id: int, period: Period) -> float:
    v = (
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
        )
        .aggregate(t=Sum("amount"))["t"]
    )
    return _f(v)


def net_profit_period(tenant_id: int, period: Period) -> float:
    return cash_in_period(tenant_id, period) - cash_out_period(tenant_id, period)


def net_margin_pct(tenant_id: int, period: Period) -> float:
    """Margem líquida = lucro / receita * 100."""
    ci = cash_in_period(tenant_id, period)
    if ci == 0:
        return 0.0
    return (net_profit_period(tenant_id, period) / ci) * 100


def revenue_growth_pct(tenant_id: int, period: Period) -> float | None:
    """Crescimento da receita vs período anterior de mesma duração."""
    duration = (period.end - period.start).days + 1
    prev = Period(
        start=period.start - timedelta(days=duration),
        end=period.start - timedelta(days=1),
    )
    return _pct(cash_in_period(tenant_id, period), cash_in_period(tenant_id, prev))


# ===========================================================================
# Despesas: fixas vs variáveis (heurística por nome de categoria)
# ===========================================================================
_FIXED_HINTS = (
    "aluguel", "salário", "salario", "salario fixo", "pro-labore", "pró-labore",
    "luz", "água", "internet", "telefone", "iss", "iptu", "alvará", "alvara",
    "contador", "assinatura", "seguro", "impostos fixos", "13º", "13 salário",
)
_VARIABLE_HINTS = (
    "comissão", "comissao", "frete", "marketing", "publicidade", "insumos",
    "compras", "matéria-prima", "materia-prima", "cmv", "custo de vendas",
    "fornecedor", "estoque",
)


def _classify_expense(name: str) -> str:
    s = (name or "").lower()
    if any(k in s for k in _FIXED_HINTS):
        return "fixed"
    if any(k in s for k in _VARIABLE_HINTS):
        return "variable"
    return "variable"  # default conservador


def expense_breakdown(tenant_id: int, period: Period) -> dict[str, float]:
    """Quebra das despesas pagas em (fixed, variable, total)."""
    rows = (
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            category__isnull=False,
        )
        .values("category__name")
        .annotate(total=Sum("amount"))
    )
    fixed = 0.0
    variable = 0.0
    for r in rows:
        kind = _classify_expense(r["category__name"])
        amt = _f(r["total"])
        if kind == "fixed":
            fixed += amt
        else:
            variable += amt
    # despesas sem categoria → variável
    no_cat = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            category__isnull=True,
        ).aggregate(t=Sum("amount"))["t"]
    )
    variable += no_cat
    return {"fixed": fixed, "variable": variable, "total": fixed + variable}


def contribution_margin_pct(tenant_id: int, period: Period) -> float:
    """Margem de contribuição = (receita - custo variável) / receita."""
    ci = cash_in_period(tenant_id, period)
    if ci == 0:
        return 0.0
    var = expense_breakdown(tenant_id, period)["variable"]
    return ((ci - var) / ci) * 100


def breakeven_point(tenant_id: int, period: Period) -> float:
    """Ponto de equilíbrio em R$ = custo fixo / margem de contribuição."""
    cm_pct = contribution_margin_pct(tenant_id, period)
    if cm_pct <= 0:
        return 0.0
    fixed = expense_breakdown(tenant_id, period)["fixed"]
    return fixed / (cm_pct / 100)


def above_breakeven(tenant_id: int, period: Period) -> dict[str, Any]:
    """Verifica se está acima ou abaixo do ponto de equilíbrio."""
    bep = breakeven_point(tenant_id, period)
    revenue = cash_in_period(tenant_id, period)
    diff = revenue - bep
    return {
        "breakeven": bep,
        "revenue": revenue,
        "diff": diff,
        "above": diff >= 0,
        "pct": _safe_div(revenue, bep) * 100 if bep else 0,
    }


# ===========================================================================
# EBITDA simplificado (= lucro operacional ≈ net + impostos/financeiros)
# ===========================================================================
_NON_OPERATIONAL_HINTS = (
    "imposto", "tributo", "juros", "financiament", "empréstimo", "emprestimo",
    "tarifa banc", "amortização", "amortizacao", "iof", "irpj", "csll",
    "simples nacional", "das", "icms", "iss", "pis", "cofins",
)


def ebitda(tenant_id: int, period: Period) -> float:
    """EBITDA = receita - despesas operacionais (exclui impostos/juros)."""
    ci = cash_in_period(tenant_id, period)
    rows = (
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            category__isnull=False,
        )
        .values("category__name")
        .annotate(total=Sum("amount"))
    )
    operational = 0.0
    for r in rows:
        name = (r["category__name"] or "").lower()
        if not any(k in name for k in _NON_OPERATIONAL_HINTS):
            operational += _f(r["total"])
    # sem categoria → conta como operacional
    no_cat = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            category__isnull=True,
        ).aggregate(t=Sum("amount"))["t"]
    )
    operational += no_cat
    return ci - operational


# ===========================================================================
# Saldo, capital de giro, burn rate, forecast
# ===========================================================================
def cash_balance(tenant_id: int, *, ref: date | None = None) -> float:
    """Saldo de caixa acumulado (todos recebimentos pagos - todos pagamentos pagos)."""
    ref = ref or timezone.now().date()
    total_in = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__lte=ref,
        ).aggregate(t=Sum("amount"))["t"]
    )
    total_out = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__lte=ref,
        ).aggregate(t=Sum("amount"))["t"]
    )
    return total_in - total_out


def working_capital(tenant_id: int, *, ref: date | None = None) -> dict[str, float]:
    """Capital de giro = a receber em aberto - a pagar em aberto."""
    ref = ref or timezone.now().date()
    recv_open = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status__in=[
                FinancialEntry.Status.PENDING,
                FinancialEntry.Status.OVERDUE,
            ],
        ).aggregate(t=Sum("amount"))["t"]
    )
    pay_open = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status__in=[
                FinancialEntry.Status.PENDING,
                FinancialEntry.Status.OVERDUE,
            ],
        ).aggregate(t=Sum("amount"))["t"]
    )
    return {
        "receivables_open": recv_open,
        "payables_open": pay_open,
        "working_capital": recv_open - pay_open,
    }


def burn_rate(tenant_id: int, *, months: int = 3) -> float:
    """Média mensal de saídas dos últimos `months` meses."""
    today = timezone.now().date()
    start = today - timedelta(days=30 * months)
    out = cash_out_period(tenant_id, Period(start=start, end=today))
    return out / max(months, 1)


def cash_forecast(tenant_id: int, *, days: int = 30) -> dict[str, Any]:
    """Forecast: saldo atual + a receber em aberto - a pagar em aberto (até days)."""
    today = timezone.now().date()
    horizon = today + timedelta(days=days)
    saldo = cash_balance(tenant_id, ref=today)

    recv_forecast = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status__in=[
                FinancialEntry.Status.PENDING,
                FinancialEntry.Status.OVERDUE,
            ],
            due_date__lte=horizon,
        ).aggregate(t=Sum("amount"))["t"]
    )
    pay_forecast = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status__in=[
                FinancialEntry.Status.PENDING,
                FinancialEntry.Status.OVERDUE,
            ],
            due_date__lte=horizon,
        ).aggregate(t=Sum("amount"))["t"]
    )

    projected = saldo + recv_forecast - pay_forecast
    return {
        "current_balance": saldo,
        "expected_in": recv_forecast,
        "expected_out": pay_forecast,
        "projected_balance": projected,
        "days": days,
        "at_risk": projected < 0,
    }


# ===========================================================================
# Score de Saúde Financeira (0–100)
# ===========================================================================
def financial_health_score(tenant_id: int) -> dict[str, Any]:
    """
    Score 0-100 ponderado:
    - Margem líquida (30%): >15% = 100, <0 = 0
    - Saldo projetado 30d (30%): positivo = 100, negativo = 0
    - Inadimplência (20%): <2% = 100, >20% = 0
    - Concentração de fornecedor (20%): <25% = 100, >70% = 0
    """
    period = month_period()

    margin = net_margin_pct(tenant_id, period)
    margin_score = max(0, min(100, (margin / 15.0) * 100))

    forecast = cash_forecast(tenant_id, days=30)
    bal = forecast["projected_balance"]
    if bal >= 0:
        bal_score = 100.0
    else:
        # Quão "negativo" é? Normalizado por burn_rate
        br = burn_rate(tenant_id, months=3) or 1
        bal_score = max(0, 100 + (bal / br) * 50)

    # Inadimplência
    base_recv = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
        ).exclude(status=FinancialEntry.Status.CANCELED).aggregate(t=Sum("amount"))["t"]
    )
    overdue_val = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status__in=[FinancialEntry.Status.PENDING, FinancialEntry.Status.OVERDUE],
            due_date__lt=timezone.now().date(),
        ).aggregate(t=Sum("amount"))["t"]
    )
    overdue_pct = _safe_div(overdue_val, base_recv) * 100
    inad_score = max(0, min(100, 100 - (overdue_pct / 20.0) * 100))

    # Concentração de fornecedor
    total_pay = cash_out_period(tenant_id, period)
    top_supplier_row = (
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            customer__isnull=False,
        )
        .values("customer_id")
        .annotate(t=Sum("amount"))
        .order_by("-t")
        .first()
    ) or {}
    top_supplier = _f(top_supplier_row.get("t"))
    conc_pct = _safe_div(top_supplier, total_pay) * 100
    if conc_pct < 25:
        conc_score = 100.0
    elif conc_pct > 70:
        conc_score = 0.0
    else:
        conc_score = 100 - ((conc_pct - 25) / 45.0) * 100

    score = (
        margin_score * 0.30
        + bal_score * 0.30
        + inad_score * 0.20
        + conc_score * 0.20
    )
    score = round(max(0, min(100, score)))

    # rótulo
    if score >= 80:
        label = "Excelente"
        color = "green"
    elif score >= 60:
        label = "Bom"
        color = "blue"
    elif score >= 40:
        label = "Regular"
        color = "amber"
    else:
        label = "Crítico"
        color = "red"

    return {
        "score": score,
        "label": label,
        "color": color,
        "components": {
            "margin": round(margin_score),
            "cash_balance": round(bal_score),
            "inadimplencia": round(inad_score),
            "supplier_concentration": round(conc_score),
        },
        "details": {
            "net_margin_pct": round(margin, 2),
            "projected_balance_30d": round(bal, 2),
            "overdue_pct": round(overdue_pct, 2),
            "top_supplier_pct": round(conc_pct, 2),
        },
    }


# ===========================================================================
# RFV (Recência, Frequência, Valor) + Segmentação de clientes
# ===========================================================================
def rfv_segments(tenant_id: int) -> dict[str, Any]:
    """Classifica clientes em segmentos RFV usando FinancialEntry receivable."""
    from django.db.models import Q

    today = timezone.now().date()
    recv = Q(financial_entries__direction=FinancialEntry.Direction.RECEIVABLE)
    rows = list(
        Customer.unsafe_objects.filter(tenant_id=tenant_id)
        .annotate(
            total=Sum("financial_entries__amount", filter=recv),
            cnt=Count("financial_entries", filter=recv),
            last=Max("financial_entries__paid_at", filter=recv),
        )
        .filter(cnt__gt=0)
        .values("id", "name", "total", "cnt", "last")
    )

    if not rows:
        return {"total": 0, "segments": {}}

    def days_since(d: date | None) -> int:
        return (today - d).days if d else 9999

    # Buckets simples por terço
    totals = sorted([_f(r["total"]) for r in rows], reverse=True)
    counts = sorted([r["cnt"] for r in rows], reverse=True)
    recencies = sorted([days_since(r["last"]) for r in rows])

    def tier(val: float, sorted_vals: list, reverse: bool) -> int:
        n = len(sorted_vals)
        if n == 0:
            return 1
        if reverse:
            idx = next((i for i, v in enumerate(sorted_vals) if val >= v), n)
        else:
            idx = next((i for i, v in enumerate(sorted_vals) if val <= v), n)
        if idx <= n // 3:
            return 3
        if idx <= (n * 2) // 3:
            return 2
        return 1

    segments: dict[str, list[dict]] = {
        "champions": [],
        "loyal": [],
        "at_risk": [],
        "lost": [],
        "new": [],
        "high_value": [],
    }

    for r in rows:
        total = _f(r["total"])
        cnt = r["cnt"]
        rec = days_since(r["last"])
        t_v = tier(total, totals, reverse=True)
        t_f = tier(cnt, counts, reverse=True)
        t_r = tier(rec, recencies, reverse=False)  # menor recência = melhor

        entry = {
            "customer_id": r["id"],
            "name": r["name"],
            "total": total,
            "count": cnt,
            "last_days": rec,
            "score_R": t_r,
            "score_F": t_f,
            "score_V": t_v,
        }

        if t_r == 3 and t_f == 3 and t_v == 3:
            segments["champions"].append(entry)
        elif t_v == 3:
            segments["high_value"].append(entry)
        elif t_r == 3 and t_f >= 2:
            segments["loyal"].append(entry)
        elif t_r == 1 and t_f >= 2:
            segments["at_risk"].append(entry)
        elif t_r == 1:
            segments["lost"].append(entry)
        elif t_f == 1 and rec < 60:
            segments["new"].append(entry)
        else:
            segments["loyal"].append(entry)

    return {
        "total": len(rows),
        "segments": {k: sorted(v, key=lambda x: -x["total"])[:20] for k, v in segments.items()},
        "counts": {k: len(v) for k, v in segments.items()},
    }


# ===========================================================================
# Produtos — Curva ABC, parados, sugestão de recompra
# ===========================================================================
def abc_curve(tenant_id: int, *, by: str = "stock_value") -> dict[str, Any]:
    """
    Curva ABC de produtos.
    - by="stock_value": classifica por valor em estoque (saldo × custo)
    - by="sales": classifica por receita de SaleItem (requer vendas)
    """
    if by == "sales":
        rows = list(
            SaleItem.unsafe_objects.filter(
                tenant_id=tenant_id,
                product__isnull=False,
                sale__status=Sale.Status.CLOSED,
            )
            .values("product_id", "product__name")
            .annotate(total=Sum("total"))
            .order_by("-total")
        )
        rows = [
            {"product_id": r["product_id"], "name": r["product__name"], "value": _f(r["total"])}
            for r in rows
        ]
    else:
        products = Product.unsafe_objects.filter(
            tenant_id=tenant_id, stock_balance__gt=0, cost__gt=0,
        )
        rows = sorted(
            (
                {
                    "product_id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "value": _f(p.stock_balance * p.cost),
                    "stock": _f(p.stock_balance),
                }
                for p in products
            ),
            key=lambda x: -x["value"],
        )

    total = sum(r["value"] for r in rows)
    if total == 0:
        return {"total": 0, "by": by, "rows": [], "counts": {"A": 0, "B": 0, "C": 0}}

    accum = 0.0
    a_count = b_count = c_count = 0
    for r in rows:
        accum += r["value"]
        share = accum / total * 100
        if share <= 80:
            r["class"] = "A"
            a_count += 1
        elif share <= 95:
            r["class"] = "B"
            b_count += 1
        else:
            r["class"] = "C"
            c_count += 1
        r["cumulative_pct"] = round(share, 2)

    return {
        "total": total,
        "by": by,
        "rows": rows[:50],
        "counts": {"A": a_count, "B": b_count, "C": c_count},
    }


def stagnant_products(tenant_id: int, *, min_stock: int = 1) -> list[dict[str, Any]]:
    """Produtos com estoque alto e nenhuma venda no SaleItem (parados)."""
    sold_ids = set(
        SaleItem.unsafe_objects.filter(
            tenant_id=tenant_id, product__isnull=False,
        ).values_list("product_id", flat=True).distinct()
    )
    qs = Product.unsafe_objects.filter(
        tenant_id=tenant_id,
        stock_balance__gte=min_stock,
        is_active=True,
    ).order_by(F("cost") * F("stock_balance"))
    return [
        {
            "product_id": p.id,
            "sku": p.sku,
            "name": p.name,
            "stock": _f(p.stock_balance),
            "cost": _f(p.cost),
            "stuck_value": _f(p.stock_balance * p.cost),
        }
        for p in qs.exclude(id__in=sold_ids)[:30]
    ]


# ===========================================================================
# DRE estruturado por categoria
# ===========================================================================
def dre_structured(tenant_id: int, period: Period) -> dict[str, Any]:
    """DRE simplificado: receitas, despesas (fixas vs variáveis), lucro.

    Estrutura:
        revenues:        [{category, total, share_pct}]
        expenses_fixed:  [{category, total, share_pct}]
        expenses_var:    [{category, total, share_pct}]
        totals: receita, despesa_total, lucro_bruto, lucro_liquido, ebitda
    """
    revs = list(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            category__isnull=False,
        )
        .values("category_id", "category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    exps = list(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            category__isnull=False,
        )
        .values("category_id", "category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    # Receitas sem categoria
    no_cat_revs = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            category__isnull=True,
        ).aggregate(t=Sum("amount"))["t"]
    )
    no_cat_exps = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.PAYABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            category__isnull=True,
        ).aggregate(t=Sum("amount"))["t"]
    )

    total_revenue = sum(_f(r["total"]) for r in revs) + no_cat_revs
    total_expense = sum(_f(e["total"]) for e in exps) + no_cat_exps

    def _pct(part: float, whole: float) -> float:
        return (part / whole * 100) if whole > 0 else 0.0

    revenues = [
        {
            "category_id": r["category_id"],
            "category": r["category__name"],
            "total": _f(r["total"]),
            "share_pct": _pct(_f(r["total"]), total_revenue),
        }
        for r in revs
    ]
    if no_cat_revs > 0:
        revenues.append({
            "category_id": None,
            "category": "(Sem categoria)",
            "total": no_cat_revs,
            "share_pct": _pct(no_cat_revs, total_revenue),
        })

    fixed: list[dict] = []
    variable: list[dict] = []
    for e in exps:
        item = {
            "category_id": e["category_id"],
            "category": e["category__name"],
            "total": _f(e["total"]),
            "share_pct": _pct(_f(e["total"]), total_expense),
        }
        if _classify_expense(e["category__name"]) == "fixed":
            fixed.append(item)
        else:
            variable.append(item)
    if no_cat_exps > 0:
        variable.append({
            "category_id": None,
            "category": "(Sem categoria)",
            "total": no_cat_exps,
            "share_pct": _pct(no_cat_exps, total_expense),
        })

    fixed_total = sum(x["total"] for x in fixed)
    variable_total = sum(x["total"] for x in variable)

    return {
        "revenues": revenues[:30],
        "expenses_fixed": fixed[:30],
        "expenses_variable": variable[:30],
        "totals": {
            "revenue": total_revenue,
            "expense_fixed": fixed_total,
            "expense_variable": variable_total,
            "expense_total": total_expense,
            "contribution_margin": total_revenue - variable_total,
            "net_profit": total_revenue - total_expense,
            "net_margin_pct": _pct(total_revenue - total_expense, total_revenue),
            "ebitda": ebitda(tenant_id, period),
        },
    }


# ===========================================================================
# ROI operacional, séries de crescimento e alertas
# ===========================================================================
def roi_operational(tenant_id: int, period: Period) -> float:
    """ROI sobre custos operacionais. = lucro_liquido / despesas * 100."""
    co = cash_out_period(tenant_id, period)
    if co == 0:
        return 0.0
    return (net_profit_period(tenant_id, period) / co) * 100


def monthly_growth_series(tenant_id: int, period: Period) -> list[dict[str, Any]]:
    """Série temporal mensal: receita, despesa, lucro + variação MoM e acumulado."""
    rows = []
    acc_revenue = 0.0
    acc_profit = 0.0
    prev_revenue = None
    prev_profit = None
    for start, end in month_buckets(period):
        p = Period(start=start, end=end)
        ci = cash_in_period(tenant_id, p)
        co = cash_out_period(tenant_id, p)
        net = ci - co
        acc_revenue += ci
        acc_profit += net
        rev_growth = None
        prof_growth = None
        if prev_revenue is not None and prev_revenue != 0:
            rev_growth = (ci - prev_revenue) / abs(prev_revenue) * 100
        if prev_profit is not None and prev_profit != 0:
            prof_growth = (net - prev_profit) / abs(prev_profit) * 100
        rows.append({
            "month": start.isoformat()[:7],
            "revenue": ci,
            "expense": co,
            "profit": net,
            "margin_pct": (net / ci * 100) if ci > 0 else 0.0,
            "revenue_growth_mom_pct": rev_growth,
            "profit_growth_mom_pct": prof_growth,
            "cumulative_revenue": acc_revenue,
            "cumulative_profit": acc_profit,
        })
        prev_revenue = ci
        prev_profit = net
    return rows


def alerts(tenant_id: int) -> list[dict[str, Any]]:
    """Lista de alertas financeiros para o dashboard Financeiro.

    Cada alerta: {kind, severity, title, message, value?}
    severity: info | warning | critical
    """
    from datetime import timedelta as _td

    out: list[dict] = []
    today = timezone.now().date()
    curr = month_period()
    prev = previous_month_period()

    # 1. Caixa negativo previsto
    forecast = cash_forecast(tenant_id, days=30)
    if forecast["at_risk"]:
        out.append({
            "kind": "cash_at_risk_30d",
            "severity": "critical",
            "title": "Caixa pode ficar negativo em 30 dias",
            "message": (
                f"Saldo projetado: R$ {forecast['projected_balance']:,.2f}. "
                f"Entradas previstas R$ {forecast['expected_in']:,.2f} vs "
                f"R$ {forecast['expected_out']:,.2f} a pagar."
            ),
            "value": forecast["projected_balance"],
        })

    # 2. Inadimplência alta (> 10%)
    base_recv = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
        ).exclude(status=FinancialEntry.Status.CANCELED).aggregate(t=Sum("amount"))["t"]
    )
    overdue_val = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status__in=[FinancialEntry.Status.PENDING, FinancialEntry.Status.OVERDUE],
            due_date__lt=today,
        ).aggregate(t=Sum("amount"))["t"]
    )
    overdue_pct = _safe_div(overdue_val, base_recv) * 100
    if overdue_pct >= 10:
        out.append({
            "kind": "overdue_high",
            "severity": "critical" if overdue_pct > 20 else "warning",
            "title": f"Inadimplência em {overdue_pct:.1f}%",
            "message": (
                f"R$ {overdue_val:,.2f} em recebíveis vencidos. "
                "Acima do limite saudável (10%)."
            ),
            "value": overdue_pct,
        })

    # 3. Queda de margem (mês corrente vs anterior)
    m_curr = net_margin_pct(tenant_id, curr)
    m_prev = net_margin_pct(tenant_id, prev)
    if m_prev != 0 and (m_curr - m_prev) < -5:  # caiu mais de 5 pp
        out.append({
            "kind": "margin_drop",
            "severity": "warning",
            "title": f"Margem caiu {abs(m_curr - m_prev):.1f} pontos",
            "message": (
                f"De {m_prev:.1f}% em {prev.start.strftime('%m/%Y')} para "
                f"{m_curr:.1f}% em {curr.start.strftime('%m/%Y')}."
            ),
            "value": m_curr - m_prev,
        })

    # 4. Crescimento anormal de despesas (> 25% MoM)
    co_curr = cash_out_period(tenant_id, curr)
    co_prev = cash_out_period(tenant_id, prev)
    if co_prev > 0:
        change = (co_curr - co_prev) / co_prev * 100
        if change > 25:
            out.append({
                "kind": "expense_surge",
                "severity": "warning" if change < 50 else "critical",
                "title": f"Despesas subiram {change:.1f}% em {curr.start.strftime('%m/%Y')}",
                "message": (
                    f"R$ {co_curr:,.2f} contra R$ {co_prev:,.2f} no mês anterior."
                ),
                "value": change,
            })

    # 5. Capital de giro negativo
    wc = working_capital(tenant_id)
    if wc["working_capital"] < 0:
        out.append({
            "kind": "negative_wc",
            "severity": "warning",
            "title": "Capital de giro negativo",
            "message": (
                f"A receber em aberto (R$ {wc['receivables_open']:,.2f}) é menor que "
                f"a pagar em aberto (R$ {wc['payables_open']:,.2f})."
            ),
            "value": wc["working_capital"],
        })

    return out


# ===========================================================================
# FASE 3 — KPIs preditivos e comerciais
# ===========================================================================
def revenue_forecast(
    tenant_id: int, *, days_ahead: int = 30, lookback_months: int = 6,
) -> dict[str, Any]:
    """
    Previsão de receita para próximos `days_ahead` dias.

    Método: regressão linear simples sobre receita mensal dos últimos
    `lookback_months` meses. Robusto, sem libs externas. Quando há
    sazonalidade clara (variação > 50% entre meses), inclui flag.

    Retorna:
      {forecast_total, forecast_daily_avg, baseline_avg_monthly,
       trend_pct_monthly, confidence, has_seasonality, last_months[]}
    """
    today = timezone.now().date()
    start = today - timedelta(days=30 * lookback_months)
    period = Period(start=start, end=today)
    monthly = monthly_growth_series(tenant_id, period)
    if not monthly:
        return {
            "forecast_total": 0.0,
            "forecast_daily_avg": 0.0,
            "baseline_avg_monthly": 0.0,
            "trend_pct_monthly": 0.0,
            "confidence": "low",
            "has_seasonality": False,
            "last_months": [],
            "days_ahead": days_ahead,
        }

    revenues = [m["revenue"] for m in monthly]
    n = len(revenues)
    avg = sum(revenues) / n if n else 0

    # regressão linear y = a + b*x (x = 0..n-1)
    if n >= 2 and avg > 0:
        xs = list(range(n))
        x_mean = sum(xs) / n
        y_mean = avg
        num = sum((xs[i] - x_mean) * (revenues[i] - y_mean) for i in range(n))
        den = sum((xs[i] - x_mean) ** 2 for i in range(n))
        slope = num / den if den else 0.0
        intercept = y_mean - slope * x_mean
        # Receita prevista no próximo mês (x = n)
        forecast_next_month = max(0.0, intercept + slope * n)
        trend_pct = (slope / avg * 100) if avg else 0.0
    else:
        forecast_next_month = avg
        slope = 0.0
        trend_pct = 0.0

    # Sazonalidade: variação máxima entre meses
    if revenues:
        rmin, rmax = min(revenues), max(revenues)
        has_seasonality = avg > 0 and (rmax - rmin) / avg > 0.5
    else:
        has_seasonality = False

    # Confiança: alta se temos 6+ meses e baixa variabilidade
    if n >= 6 and not has_seasonality:
        confidence = "high"
    elif n >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    forecast_total = (forecast_next_month / 30.0) * days_ahead

    return {
        "forecast_total": forecast_total,
        "forecast_daily_avg": forecast_next_month / 30.0,
        "baseline_avg_monthly": avg,
        "trend_pct_monthly": trend_pct,
        "confidence": confidence,
        "has_seasonality": has_seasonality,
        "last_months": [
            {"month": m["month"], "revenue": m["revenue"]} for m in monthly
        ],
        "days_ahead": days_ahead,
        "method": "linear_regression",
    }


def expense_forecast(tenant_id: int, *, days_ahead: int = 30) -> dict[str, Any]:
    """Previsão simples de despesas (similar a revenue_forecast)."""
    today = timezone.now().date()
    start = today - timedelta(days=180)
    period = Period(start=start, end=today)
    monthly = monthly_growth_series(tenant_id, period)
    if not monthly:
        return {
            "forecast_total": 0.0,
            "baseline_avg_monthly": 0.0,
            "trend_pct_monthly": 0.0,
            "days_ahead": days_ahead,
        }
    expenses = [m["expense"] for m in monthly]
    avg = sum(expenses) / len(expenses) if expenses else 0
    forecast = (avg / 30.0) * days_ahead
    return {
        "forecast_total": forecast,
        "baseline_avg_monthly": avg,
        "trend_pct_monthly": 0.0,  # simplificado
        "days_ahead": days_ahead,
    }


def ltv_estimate(tenant_id: int, *, months_back: int = 12) -> dict[str, Any]:
    """
    LTV médio estimado por cliente.

    Para tenants com Sale: receita média / nº clientes únicos com venda.
    Para tenants sem Sale (varejo): cash_in dividido por clientes únicos
    identificados em FinancialEntry receivable.
    """
    today = timezone.now().date()
    period = Period(
        start=today - timedelta(days=30 * months_back),
        end=today,
    )

    # Receita total via FinancialEntry (mais robusto pra varejo)
    total_revenue = cash_in_period(tenant_id, period)

    # Clientes únicos identificados
    customer_ids = (
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status=FinancialEntry.Status.PAID,
            paid_at__gte=period.start,
            paid_at__lte=period.end,
            customer__isnull=False,
        )
        .values_list("customer_id", flat=True)
        .distinct()
    )
    n_customers = len(list(customer_ids))

    # Clientes via Sale (se houver)
    sale_customer_ids = (
        Sale.unsafe_objects.filter(
            tenant_id=tenant_id,
            status=Sale.Status.CLOSED,
            issued_at__gte=_aware(period.start),
            issued_at__lte=_aware(period.end, end=True),
            customer__isnull=False,
        )
        .values_list("customer_id", flat=True)
        .distinct()
    )
    n_sale_customers = len(list(sale_customer_ids))

    # Use o maior dos dois (ou via Sale se houver)
    effective = max(n_customers, n_sale_customers)
    ltv = (total_revenue / effective) if effective > 0 else 0.0

    return {
        "ltv_avg": ltv,
        "total_revenue": total_revenue,
        "unique_customers": effective,
        "via_sales": n_sale_customers,
        "via_financial": n_customers,
        "months_back": months_back,
    }


def repurchase_rate(tenant_id: int, *, window_days: int = 90) -> dict[str, Any]:
    """
    Taxa de recompra: % de clientes que voltaram a comprar dentro da janela.

    Calculado em FinancialEntry receivable (mais robusto que Sale para varejo):
    clientes com 2+ recebimentos em janelas distintas / total de clientes únicos.
    """
    from django.db.models import Count

    today = timezone.now().date()
    cutoff = today - timedelta(days=window_days * 2)  # 2 janelas

    base_qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.RECEIVABLE,
        status=FinancialEntry.Status.PAID,
        paid_at__gte=cutoff,
        customer__isnull=False,
    )

    customers_with_counts = (
        base_qs.values("customer_id")
        .annotate(c=Count("id"))
    )

    total = customers_with_counts.count()
    repurchased = sum(1 for r in customers_with_counts if r["c"] >= 2)
    rate = (repurchased / total * 100) if total else 0.0

    return {
        "rate_pct": rate,
        "total_customers": total,
        "repurchased": repurchased,
        "window_days": window_days,
    }


def commercial_kpis(tenant_id: int, period: Period) -> dict[str, Any]:
    """
    Bundle de KPIs comerciais — usa Sale quando disponível, fallback
    em FinancialEntry receivable.
    """
    from apps.analytics import kpis as kpi_v1

    rev_sale = float(kpi_v1.revenue(tenant_id, period))
    n_sales = kpi_v1.num_sales(tenant_id, period)
    avg_ticket_sale = float(kpi_v1.avg_ticket(tenant_id, period))
    cash_in = cash_in_period(tenant_id, period)

    return {
        "revenue_sale": rev_sale,
        "revenue_cash": cash_in,
        "num_sales": n_sales,
        "avg_ticket_sale": avg_ticket_sale,
        "by_salesperson": kpi_v1.sales_by_salesperson(tenant_id, period),
        "top_products": kpi_v1.top_products(tenant_id, period, limit=10),
        "top_customers": kpi_v1.top_customers(tenant_id, period, limit=10),
        "top_revenue_categories": kpi_v1.top_categories(
            tenant_id, period, direction="receivable", limit=10,
        ),
    }


def predictive_overview(tenant_id: int) -> dict[str, Any]:
    """Bundle de previsões para a central de insights."""
    today = timezone.now().date()
    # Forecasts
    rev_30 = revenue_forecast(tenant_id, days_ahead=30)
    rev_60 = revenue_forecast(tenant_id, days_ahead=60)
    rev_90 = revenue_forecast(tenant_id, days_ahead=90)
    exp_30 = expense_forecast(tenant_id, days_ahead=30)
    cash_30 = cash_forecast(tenant_id, days=30)
    cash_60 = cash_forecast(tenant_id, days=60)
    cash_90 = cash_forecast(tenant_id, days=90)

    # Cohort / inadimplência
    overdue_recv = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status__in=[FinancialEntry.Status.PENDING, FinancialEntry.Status.OVERDUE],
            due_date__lt=today,
        ).aggregate(t=Sum("amount"))["t"]
    )
    open_recv = _f(
        FinancialEntry.unsafe_objects.filter(
            tenant_id=tenant_id,
            direction=FinancialEntry.Direction.RECEIVABLE,
            status__in=[FinancialEntry.Status.PENDING, FinancialEntry.Status.OVERDUE],
        ).aggregate(t=Sum("amount"))["t"]
    )
    overdue_risk_pct = (overdue_recv / open_recv * 100) if open_recv else 0.0

    return {
        "revenue_forecast": {
            "30d": rev_30,
            "60d": rev_60,
            "90d": rev_90,
        },
        "expense_forecast_30d": exp_30,
        "cash_forecast": {
            "30d": cash_30,
            "60d": cash_60,
            "90d": cash_90,
        },
        "overdue_risk": {
            "overdue_amount": overdue_recv,
            "open_amount": open_recv,
            "risk_pct": overdue_risk_pct,
        },
        "ltv": ltv_estimate(tenant_id),
        "repurchase": repurchase_rate(tenant_id, window_days=90),
    }
