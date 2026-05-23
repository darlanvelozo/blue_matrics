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

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.db.models.query import QuerySet
from django.utils import timezone

from apps.sync.models import FinancialEntry, Sale, SaleItem

from .periods import Period, month_buckets


# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Filters:
    """Filtros opcionais aplicáveis aos KPIs (drill-down/segmentação)."""

    salesperson_id: int | None = None
    customer_id: int | None = None
    product_id: int | None = None
    category_id: int | None = None

    def is_empty(self) -> bool:
        return not any(
            (self.salesperson_id, self.customer_id, self.product_id, self.category_id)
        )


_EMPTY = Filters()


def _apply_sale_filters(qs: QuerySet, f: Filters) -> QuerySet:
    if f.salesperson_id:
        qs = qs.filter(salesperson_id=f.salesperson_id)
    if f.customer_id:
        qs = qs.filter(customer_id=f.customer_id)
    if f.product_id:
        qs = qs.filter(items__product_id=f.product_id).distinct()
    return qs


def _apply_fin_filters(qs: QuerySet, f: Filters) -> QuerySet:
    if f.category_id:
        qs = qs.filter(category_id=f.category_id)
    if f.customer_id:
        qs = qs.filter(customer_id=f.customer_id)
    return qs


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
def revenue(tenant_id: int, period: Period, filters: Filters = _EMPTY) -> Decimal:
    """Faturamento = soma das vendas fechadas no período."""
    qs = Sale.unsafe_objects.filter(
        tenant_id=tenant_id,
        status=Sale.Status.CLOSED,
        issued_at__gte=_aware(period.start),
        issued_at__lte=_aware(period.end, end_of_day=True),
    )
    qs = _apply_sale_filters(qs, filters)
    return _dec(qs.aggregate(t=Sum("total"))["t"])


def num_sales(tenant_id: int, period: Period, filters: Filters = _EMPTY) -> int:
    qs = Sale.unsafe_objects.filter(
        tenant_id=tenant_id,
        status=Sale.Status.CLOSED,
        issued_at__gte=_aware(period.start),
        issued_at__lte=_aware(period.end, end_of_day=True),
    )
    qs = _apply_sale_filters(qs, filters)
    return qs.count()


def avg_ticket(tenant_id: int, period: Period, filters: Filters = _EMPTY) -> Decimal:
    n = num_sales(tenant_id, period, filters)
    if n == 0:
        return Decimal("0")
    return revenue(tenant_id, period, filters) / n


def cash_in(tenant_id: int, period: Period, filters: Filters = _EMPTY) -> Decimal:
    """Recebimentos efetivos no período."""
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.RECEIVABLE,
        status=FinancialEntry.Status.PAID,
        paid_at__gte=period.start,
        paid_at__lte=period.end,
    )
    qs = _apply_fin_filters(qs, filters)
    return _dec(qs.aggregate(t=Sum("amount"))["t"])


def cash_out(tenant_id: int, period: Period, filters: Filters = _EMPTY) -> Decimal:
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.PAYABLE,
        status=FinancialEntry.Status.PAID,
        paid_at__gte=period.start,
        paid_at__lte=period.end,
    )
    qs = _apply_fin_filters(qs, filters)
    return _dec(qs.aggregate(t=Sum("amount"))["t"])


def net_profit(tenant_id: int, period: Period, filters: Filters = _EMPTY) -> Decimal:
    return cash_in(tenant_id, period, filters) - cash_out(tenant_id, period, filters)


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
def revenue_by_month(
    tenant_id: int, period: Period, filters: Filters = _EMPTY,
) -> list[dict[str, Any]]:
    """Faturamento mensal — usa buckets do período."""
    out = []
    for start, end in month_buckets(period):
        p = Period(start=start, end=end)
        out.append({
            "month": start.isoformat()[:7],
            "revenue": _to_float(revenue(tenant_id, p, filters)),
            "sales_count": num_sales(tenant_id, p, filters),
        })
    return out


def cashflow_by_month(
    tenant_id: int, period: Period, filters: Filters = _EMPTY,
) -> list[dict[str, Any]]:
    out = []
    for start, end in month_buckets(period):
        p = Period(start=start, end=end)
        ci = cash_in(tenant_id, p, filters)
        co = cash_out(tenant_id, p, filters)
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
def top_customers(
    tenant_id: int, period: Period, *, limit: int = 5, filters: Filters = _EMPTY,
) -> list[dict[str, Any]]:
    qs = Sale.unsafe_objects.filter(
        tenant_id=tenant_id,
        status=Sale.Status.CLOSED,
        issued_at__gte=_aware(period.start),
        issued_at__lte=_aware(period.end, end_of_day=True),
        customer__isnull=False,
    )
    qs = _apply_sale_filters(qs, filters)
    qs = (
        qs.values("customer_id", "customer__name")
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


def top_products(
    tenant_id: int, period: Period, *, limit: int = 5, filters: Filters = _EMPTY,
) -> list[dict[str, Any]]:
    qs = SaleItem.unsafe_objects.filter(
        tenant_id=tenant_id,
        sale__status=Sale.Status.CLOSED,
        sale__issued_at__gte=_aware(period.start),
        sale__issued_at__lte=_aware(period.end, end_of_day=True),
        product__isnull=False,
    )
    if filters.salesperson_id:
        qs = qs.filter(sale__salesperson_id=filters.salesperson_id)
    if filters.customer_id:
        qs = qs.filter(sale__customer_id=filters.customer_id)
    if filters.product_id:
        qs = qs.filter(product_id=filters.product_id)
    qs = (
        qs.values("product_id", "product__name")
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


def sales_by_salesperson(
    tenant_id: int, period: Period, filters: Filters = _EMPTY,
) -> list[dict[str, Any]]:
    qs = Sale.unsafe_objects.filter(
        tenant_id=tenant_id,
        status=Sale.Status.CLOSED,
        issued_at__gte=_aware(period.start),
        issued_at__lte=_aware(period.end, end_of_day=True),
        salesperson__isnull=False,
    )
    qs = _apply_sale_filters(qs, filters)
    qs = (
        qs.values("salesperson_id", "salesperson__name")
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
def dre_monthly(
    tenant_id: int, period: Period, filters: Filters = _EMPTY,
) -> list[dict[str, Any]]:
    return cashflow_by_month(tenant_id, period, filters)


# ===========================================================================
# Top N / agregações financeiras (FinancialEntry-based)
# ===========================================================================
def top_categories(
    tenant_id: int,
    period: Period,
    *,
    direction: str,  # "receivable" ou "payable"
    limit: int = 10,
    filters: Filters = _EMPTY,
) -> list[dict[str, Any]]:
    """Top categorias por valor pago no período (recebido se receivable, pago se payable)."""
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=direction,
        status=FinancialEntry.Status.PAID,
        paid_at__gte=period.start,
        paid_at__lte=period.end,
        category__isnull=False,
    )
    qs = _apply_fin_filters(qs, filters)
    rows = (
        qs.values("category_id", "category__name")
        .annotate(total=Sum("amount"), n=Count("id"))
        .order_by("-total")[:limit]
    )
    return [
        {
            "category_id": r["category_id"],
            "name": r["category__name"],
            "total": _to_float(r["total"]),
            "count": r["n"],
        }
        for r in rows
    ]


def top_financial_customers(
    tenant_id: int,
    period: Period,
    *,
    direction: str,  # "receivable" → top clientes; "payable" → top fornecedores
    limit: int = 10,
    filters: Filters = _EMPTY,
) -> list[dict[str, Any]]:
    """Top clientes/fornecedores por valor pago no período."""
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=direction,
        status=FinancialEntry.Status.PAID,
        paid_at__gte=period.start,
        paid_at__lte=period.end,
        customer__isnull=False,
    )
    qs = _apply_fin_filters(qs, filters)
    rows = (
        qs.values("customer_id", "customer__name")
        .annotate(total=Sum("amount"), n=Count("id"))
        .order_by("-total")[:limit]
    )
    return [
        {
            "customer_id": r["customer_id"],
            "name": r["customer__name"],
            "total": _to_float(r["total"]),
            "count": r["n"],
        }
        for r in rows
    ]


def upcoming_payables(
    tenant_id: int, *, days: int = 30, ref_date: date | None = None,
) -> dict[str, Any]:
    """Contas a pagar nos próximos `days` dias (status pendente/atrasado)."""
    ref = ref_date or timezone.now().date()
    horizon = ref + timezone.timedelta(days=days) if hasattr(timezone, "timedelta") else None
    from datetime import timedelta as _td
    horizon = ref + _td(days=days)
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.PAYABLE,
        status__in=[FinancialEntry.Status.PENDING, FinancialEntry.Status.OVERDUE],
        due_date__gte=ref,
        due_date__lte=horizon,
    )
    return {
        "days": days,
        "total": _to_float(qs.aggregate(t=Sum("amount"))["t"]),
        "count": qs.count(),
    }


def upcoming_receivables(
    tenant_id: int, *, days: int = 30, ref_date: date | None = None,
) -> dict[str, Any]:
    """Contas a receber nos próximos `days` dias (status pendente/atrasado)."""
    ref = ref_date or timezone.now().date()
    from datetime import timedelta as _td
    horizon = ref + _td(days=days)
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.RECEIVABLE,
        status__in=[FinancialEntry.Status.PENDING, FinancialEntry.Status.OVERDUE],
        due_date__gte=ref,
        due_date__lte=horizon,
    )
    return {
        "days": days,
        "total": _to_float(qs.aggregate(t=Sum("amount"))["t"]),
        "count": qs.count(),
    }


def overdue_payables_summary(
    tenant_id: int, *, ref_date: date | None = None,
) -> dict[str, Any]:
    """Contas a pagar vencidas (atrasadas)."""
    ref = ref_date or timezone.now().date()
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.PAYABLE,
        status__in=[FinancialEntry.Status.PENDING, FinancialEntry.Status.OVERDUE],
        due_date__lt=ref,
    )
    return {
        "total": _to_float(qs.aggregate(t=Sum("amount"))["t"]),
        "count": qs.count(),
    }


def overdue_receivables_summary(
    tenant_id: int, *, ref_date: date | None = None,
) -> dict[str, Any]:
    """Contas a receber vencidas (atrasadas)."""
    ref = ref_date or timezone.now().date()
    qs = FinancialEntry.unsafe_objects.filter(
        tenant_id=tenant_id,
        direction=FinancialEntry.Direction.RECEIVABLE,
        status__in=[FinancialEntry.Status.PENDING, FinancialEntry.Status.OVERDUE],
        due_date__lt=ref,
    )
    return {
        "total": _to_float(qs.aggregate(t=Sum("amount"))["t"]),
        "count": qs.count(),
    }


# ===========================================================================
# Resumos com comparação
# ===========================================================================
def kpi_with_change(
    tenant_id: int,
    period: Period,
    *,
    metric_fn,
    comparison: str = "prev_period",
    filters: Filters = _EMPTY,
) -> dict[str, Any]:
    prev = period.shift_for_comparison(comparison)
    curr_val = metric_fn(tenant_id, period, filters)
    prev_val = metric_fn(tenant_id, prev, filters)
    change_pct = _pct_change(_dec(curr_val), _dec(prev_val))
    return {
        "current": _to_float(curr_val),
        "previous": _to_float(prev_val),
        "change_pct": change_pct,
    }


def executive_summary(
    tenant_id: int,
    period: Period,
    comparison: str = "prev_period",
    filters: Filters = _EMPTY,
) -> dict[str, Any]:
    return {
        "period": {"start": period.start.isoformat(), "end": period.end.isoformat()},
        "comparison_mode": comparison,
        # Receita: faturamento (Sale) e/ou recebimentos efetivos (cash_in)
        "revenue": kpi_with_change(tenant_id, period, metric_fn=revenue, comparison=comparison, filters=filters),
        "cash_in": kpi_with_change(tenant_id, period, metric_fn=cash_in, comparison=comparison, filters=filters),
        "cash_out": kpi_with_change(tenant_id, period, metric_fn=cash_out, comparison=comparison, filters=filters),
        "net_profit": kpi_with_change(tenant_id, period, metric_fn=net_profit, comparison=comparison, filters=filters),
        "avg_ticket": kpi_with_change(tenant_id, period, metric_fn=avg_ticket, comparison=comparison, filters=filters),
        "num_sales": kpi_with_change(tenant_id, period, metric_fn=num_sales, comparison=comparison, filters=filters),
        "overdue_rate": overdue_rate(tenant_id),
        "overdue_receivables": overdue_receivables_summary(tenant_id),
        "overdue_payables": overdue_payables_summary(tenant_id),
        "upcoming_receivables_30d": upcoming_receivables(tenant_id, days=30),
        "upcoming_payables_30d": upcoming_payables(tenant_id, days=30),
        "revenue_by_month": revenue_by_month(tenant_id, period, filters),
        "cashflow_by_month": cashflow_by_month(tenant_id, period, filters),
        "top_customers": top_customers(tenant_id, period, filters=filters),
        "top_products": top_products(tenant_id, period, filters=filters),
        "top_receivable_categories": top_categories(tenant_id, period, direction="receivable", limit=5, filters=filters),
        "top_payable_categories": top_categories(tenant_id, period, direction="payable", limit=5, filters=filters),
    }


def financial_summary(
    tenant_id: int,
    period: Period,
    comparison: str = "prev_period",
    filters: Filters = _EMPTY,
) -> dict[str, Any]:
    return {
        "period": {"start": period.start.isoformat(), "end": period.end.isoformat()},
        "comparison_mode": comparison,
        "cash_in": kpi_with_change(tenant_id, period, metric_fn=cash_in, comparison=comparison, filters=filters),
        "cash_out": kpi_with_change(tenant_id, period, metric_fn=cash_out, comparison=comparison, filters=filters),
        "net_profit": kpi_with_change(tenant_id, period, metric_fn=net_profit, comparison=comparison, filters=filters),
        "overdue_rate": overdue_rate(tenant_id),
        "overdue_receivables": overdue_receivables_summary(tenant_id),
        "overdue_payables": overdue_payables_summary(tenant_id),
        "upcoming_receivables_30d": upcoming_receivables(tenant_id, days=30),
        "upcoming_receivables_60d": upcoming_receivables(tenant_id, days=60),
        "upcoming_receivables_90d": upcoming_receivables(tenant_id, days=90),
        "upcoming_payables_30d": upcoming_payables(tenant_id, days=30),
        "upcoming_payables_60d": upcoming_payables(tenant_id, days=60),
        "upcoming_payables_90d": upcoming_payables(tenant_id, days=90),
        "cashflow_by_month": cashflow_by_month(tenant_id, period, filters),
        "dre_monthly": dre_monthly(tenant_id, period, filters),
        "top_receivable_categories": top_categories(tenant_id, period, direction="receivable", limit=10, filters=filters),
        "top_payable_categories": top_categories(tenant_id, period, direction="payable", limit=10, filters=filters),
        "top_receivable_customers": top_financial_customers(tenant_id, period, direction="receivable", limit=10, filters=filters),
        "top_payable_suppliers": top_financial_customers(tenant_id, period, direction="payable", limit=10, filters=filters),
    }


def commercial_summary(
    tenant_id: int,
    period: Period,
    comparison: str = "prev_period",
    filters: Filters = _EMPTY,
) -> dict[str, Any]:
    return {
        "period": {"start": period.start.isoformat(), "end": period.end.isoformat()},
        "comparison_mode": comparison,
        "revenue": kpi_with_change(tenant_id, period, metric_fn=revenue, comparison=comparison, filters=filters),
        "num_sales": kpi_with_change(tenant_id, period, metric_fn=num_sales, comparison=comparison, filters=filters),
        "avg_ticket": kpi_with_change(tenant_id, period, metric_fn=avg_ticket, comparison=comparison, filters=filters),
        # Fallback FinancialEntry — útil quando o tenant não usa o módulo de Vendas
        "cash_in": kpi_with_change(tenant_id, period, metric_fn=cash_in, comparison=comparison, filters=filters),
        "revenue_by_month": revenue_by_month(tenant_id, period, filters),
        "top_customers": top_customers(tenant_id, period, limit=10, filters=filters),
        "top_products": top_products(tenant_id, period, limit=10, filters=filters),
        "by_salesperson": sales_by_salesperson(tenant_id, period, filters),
        # Top clientes por valor recebido — para tenants sem vendas formais
        "top_receivable_customers": top_financial_customers(tenant_id, period, direction="receivable", limit=10, filters=filters),
    }


# ===========================================================================
# Empty signal — frontend usa pra mostrar "sincronize primeiro"
# ===========================================================================
def has_any_data(tenant_id: int) -> bool:
    return Sale.unsafe_objects.filter(tenant_id=tenant_id).exists() or (
        FinancialEntry.unsafe_objects.filter(tenant_id=tenant_id).exists()
    )
