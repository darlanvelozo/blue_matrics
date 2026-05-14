"""
Funções puras de KPI sobre dados Silver.

Cada função recebe `tenant_id` e um `Period` e devolve um dict serializável.
Nada de cache ainda — quando o volume crescer, viram materialized views.

Regras:
- Faturamento = soma de `Sale.total` com `status='closed'` no período (`issued_at`)
- Receita = `FinancialEntry.amount` direction='receivable' & status='paid', filtrado por `paid_at`
- Despesa = `FinancialEntry.amount` direction='payable' & status='paid', filtrado por `paid_at`
- Lucro líquido = Receita - Despesa
- Inadimplência% = (overdue receivables / total receivables abertos) por valor
- Ticket médio = faturamento / nº de vendas closed no período
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from apps.sync.models import FinancialEntry, Sale, SaleItem

from .periods import Period, month_buckets


# ---------------------------------------------------------------------------
def _dec(v) -> Decimal:  # type: ignore[no-untyped-def]
    return Decimal(str(v or 0))


def _to_float(v) -> float:  # type: ignore[no-untyped-def]
    if v is None:
        return 0.0
    return float(v)


def _aware(d: date, *, end_of_day: bool = False) -> datetime:
    """Converte date → datetime timezone-aware (TZ do Django)."""
    t = time.max if end_of_day else time.min
    return timezone.make_aware(datetime.combine(d, t))


def _pct_change(curr: Decimal, prev: Decimal) -> float | None:
    if not prev:
        return None
    return float((curr - prev) / prev * 100)


# ===========================================================================
# KPIs primitivos (1 número, escopado por período)
# ===========================================================================
def revenue(tenant_id: int, period: Period) -> Decimal:
    """Faturamento = soma das vendas fechadas no período."""
    qs = Sale.unsafe_objects.filter(
        tenant_id=tenant_id,
        status=Sale.Status.CLOSED,
        issued_at__gte=_aware(period.start),
        issued_at__lte=_aware(period.end, end_of_day=True),
    )
    return _dec(qs.aggregate(t=Sum("total"))["t"])


def num_sales(tenant_id: int, period: Period) -> int:
    return Sale.unsafe_objects.filter(
        tenant_id=tenant_id,
        status=Sale.Status.CLOSED,
        issued_at__gte=_aware(period.start),
        issued_at__lte=_aware(period.end, end_of_day=True),
    ).count()


def avg_ticket(tenant_id: int, period: Period) -> Decimal:
    n = num_sales(tenant_id, period)
    if n == 0:
        return Decimal("0")
    return revenue(tenant_id, period) / n


def cash_in(tenant_id: int, period: Period) -> Decimal:
    """Recebimentos efetivos no período."""
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.RECEIVABLE,
        status=FinancialEntry.Status.PAID,
        paid_at__gte=period.start,
        paid_at__lte=period.end,
    )
    return _dec(qs.aggregate(t=Sum("amount"))["t"])


def cash_out(tenant_id: int, period: Period) -> Decimal:
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.PAYABLE,
        status=FinancialEntry.Status.PAID,
        paid_at__gte=period.start,
        paid_at__lte=period.end,
    )
    return _dec(qs.aggregate(t=Sum("amount"))["t"])


def net_profit(tenant_id: int, period: Period) -> Decimal:
    return cash_in(tenant_id, period) - cash_out(tenant_id, period)


def overdue_rate(tenant_id: int, *, ref_date: date | None = None) -> float:
    """% (em valor) de contas a receber vencidas e ainda em aberto na data ref."""
    ref = ref_date or timezone.now().date()
    base = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.RECEIVABLE,
    ).exclude(status=FinancialEntry.Status.CANCELED)

    total = _dec(base.aggregate(t=Sum("amount"))["t"])
    if total == 0:
        return 0.0
    overdue = _dec(
        base.filter(
            status__in=[FinancialEntry.Status.PENDING, FinancialEntry.Status.OVERDUE],
            due_date__lt=ref,
        ).aggregate(t=Sum("amount"))["t"]
    )
    return float(overdue / total * 100)


# ===========================================================================
# Séries temporais
# ===========================================================================
def revenue_by_month(tenant_id: int, period: Period) -> list[dict[str, Any]]:
    """Faturamento mensal — usa buckets do período."""
    out = []
    for start, end in month_buckets(period):
        p = Period(start=start, end=end)
        out.append({
            "month": start.isoformat()[:7],  # YYYY-MM
            "revenue": _to_float(revenue(tenant_id, p)),
            "sales_count": num_sales(tenant_id, p),
        })
    return out


def cashflow_by_month(tenant_id: int, period: Period) -> list[dict[str, Any]]:
    out = []
    for start, end in month_buckets(period):
        p = Period(start=start, end=end)
        ci = cash_in(tenant_id, p)
        co = cash_out(tenant_id, p)
        out.append({
            "month": start.isoformat()[:7],
            "in": _to_float(ci),
            "out": _to_float(co),
            "net": _to_float(ci - co),
        })
    return out


# ===========================================================================
# Top N
# ===========================================================================
def top_customers(tenant_id: int, period: Period, *, limit: int = 5) -> list[dict[str, Any]]:
    qs = (
        Sale.unsafe_objects.filter(
            tenant_id=tenant_id,
            status=Sale.Status.CLOSED,
            issued_at__gte=_aware(period.start),
            issued_at__lte=_aware(period.end, end_of_day=True),
            customer__isnull=False,
        )
        .values("customer_id", "customer__name")
        .annotate(total=Sum("total"), n=Count("id"))
        .order_by("-total")[:limit]
    )
    return [
        {
            "customer_id": r["customer_id"],
            "name": r["customer__name"],
            "total": _to_float(r["total"]),
            "sales": r["n"],
        }
        for r in qs
    ]


def top_products(tenant_id: int, period: Period, *, limit: int = 5) -> list[dict[str, Any]]:
    qs = (
        SaleItem.unsafe_objects.filter(
            tenant_id=tenant_id,
            sale__status=Sale.Status.CLOSED,
            sale__issued_at__gte=_aware(period.start),
            sale__issued_at__lte=_aware(period.end, end_of_day=True),
            product__isnull=False,
        )
        .values("product_id", "product__name")
        .annotate(total=Sum("total"), qty=Sum("quantity"))
        .order_by("-total")[:limit]
    )
    return [
        {
            "product_id": r["product_id"],
            "name": r["product__name"],
            "total": _to_float(r["total"]),
            "quantity": _to_float(r["qty"]),
        }
        for r in qs
    ]


def sales_by_salesperson(tenant_id: int, period: Period) -> list[dict[str, Any]]:
    qs = (
        Sale.unsafe_objects.filter(
            tenant_id=tenant_id,
            status=Sale.Status.CLOSED,
            issued_at__gte=_aware(period.start),
            issued_at__lte=_aware(period.end, end_of_day=True),
            salesperson__isnull=False,
        )
        .values("salesperson_id", "salesperson__name")
        .annotate(total=Sum("total"), n=Count("id"))
        .order_by("-total")
    )
    return [
        {
            "salesperson_id": r["salesperson_id"],
            "name": r["salesperson__name"],
            "total": _to_float(r["total"]),
            "sales": r["n"],
        }
        for r in qs
    ]


# ===========================================================================
# DRE simplificado por mês (receitas - despesas)
# ===========================================================================
def dre_monthly(tenant_id: int, period: Period) -> list[dict[str, Any]]:
    return cashflow_by_month(tenant_id, period)


# ===========================================================================
# Resumos com comparação
# ===========================================================================
def kpi_with_change(
    tenant_id: int,
    period: Period,
    *,
    metric_fn,
    comparison: str = "prev_period",
) -> dict[str, Any]:
    prev = period.shift_for_comparison(comparison)
    curr_val = metric_fn(tenant_id, period)
    prev_val = metric_fn(tenant_id, prev)
    change_pct = _pct_change(_dec(curr_val), _dec(prev_val))
    return {
        "current": _to_float(curr_val),
        "previous": _to_float(prev_val),
        "change_pct": change_pct,
    }


def executive_summary(tenant_id: int, period: Period, comparison: str = "prev_period") -> dict[str, Any]:
    return {
        "period": {"start": period.start.isoformat(), "end": period.end.isoformat()},
        "comparison_mode": comparison,
        "revenue": kpi_with_change(tenant_id, period, metric_fn=revenue, comparison=comparison),
        "net_profit": kpi_with_change(tenant_id, period, metric_fn=net_profit, comparison=comparison),
        "avg_ticket": kpi_with_change(tenant_id, period, metric_fn=avg_ticket, comparison=comparison),
        "num_sales": kpi_with_change(tenant_id, period, metric_fn=num_sales, comparison=comparison),
        "overdue_rate": overdue_rate(tenant_id),
        "revenue_by_month": revenue_by_month(tenant_id, period),
        "top_customers": top_customers(tenant_id, period),
        "top_products": top_products(tenant_id, period),
    }


def financial_summary(tenant_id: int, period: Period, comparison: str = "prev_period") -> dict[str, Any]:
    return {
        "period": {"start": period.start.isoformat(), "end": period.end.isoformat()},
        "comparison_mode": comparison,
        "cash_in": kpi_with_change(tenant_id, period, metric_fn=cash_in, comparison=comparison),
        "cash_out": kpi_with_change(tenant_id, period, metric_fn=cash_out, comparison=comparison),
        "net_profit": kpi_with_change(tenant_id, period, metric_fn=net_profit, comparison=comparison),
        "overdue_rate": overdue_rate(tenant_id),
        "cashflow_by_month": cashflow_by_month(tenant_id, period),
        "dre_monthly": dre_monthly(tenant_id, period),
    }


def commercial_summary(tenant_id: int, period: Period, comparison: str = "prev_period") -> dict[str, Any]:
    return {
        "period": {"start": period.start.isoformat(), "end": period.end.isoformat()},
        "comparison_mode": comparison,
        "revenue": kpi_with_change(tenant_id, period, metric_fn=revenue, comparison=comparison),
        "num_sales": kpi_with_change(tenant_id, period, metric_fn=num_sales, comparison=comparison),
        "avg_ticket": kpi_with_change(tenant_id, period, metric_fn=avg_ticket, comparison=comparison),
        "revenue_by_month": revenue_by_month(tenant_id, period),
        "top_customers": top_customers(tenant_id, period, limit=10),
        "top_products": top_products(tenant_id, period, limit=10),
        "by_salesperson": sales_by_salesperson(tenant_id, period),
    }


# ===========================================================================
# Empty signal — frontend usa pra mostrar "sincronize primeiro"
# ===========================================================================
def has_any_data(tenant_id: int) -> bool:
    return Sale.unsafe_objects.filter(tenant_id=tenant_id).exists() or (
        FinancialEntry.unsafe_objects.filter(tenant_id=tenant_id).exists()
    )
