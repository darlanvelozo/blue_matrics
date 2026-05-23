"""Endpoints de dashboards."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.utils import get_request_tenant

from . import kpis, kpis_v2
from .periods import resolve_period
from .smart_cards import build_smart_cards


def _bad_request(message: str, code: str = "invalid_request") -> Response:
    return Response(
        {"error": {"code": code, "message": message}},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _int_or_none(v: str | None) -> int | None:
    if not v:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _parse_filters(request: Request) -> kpis.Filters:
    return kpis.Filters(
        salesperson_id=_int_or_none(request.query_params.get("salesperson")),
        customer_id=_int_or_none(request.query_params.get("customer")),
        product_id=_int_or_none(request.query_params.get("product")),
        category_id=_int_or_none(request.query_params.get("category")),
    )


def _parse_params(request: Request):  # type: ignore[no-untyped-def]
    preset = request.query_params.get("preset")
    start = request.query_params.get("start")
    end = request.query_params.get("end")
    comparison = request.query_params.get("comparison", "prev_period")
    if comparison not in ("prev_period", "yoy"):
        comparison = "prev_period"
    try:
        period = resolve_period(preset=preset, start=start, end=end)
    except ValueError as e:
        raise ValueError(f"Datas inválidas: {e}") from e
    filters = _parse_filters(request)
    return period, comparison, filters


class ExecutiveDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _bad_request("Tenant não encontrado.", "no_tenant")
        try:
            period, comparison, filters = _parse_params(request)
        except ValueError as e:
            return _bad_request(str(e))
        data = kpis.executive_summary(tenant.id, period, comparison, filters)
        data["has_data"] = kpis.has_any_data(tenant.id)
        data["filters_applied"] = not filters.is_empty()
        return Response(data)


class FinancialDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _bad_request("Tenant não encontrado.", "no_tenant")
        try:
            period, comparison, filters = _parse_params(request)
        except ValueError as e:
            return _bad_request(str(e))
        data = kpis.financial_summary(tenant.id, period, comparison, filters)
        data["has_data"] = kpis.has_any_data(tenant.id)
        data["filters_applied"] = not filters.is_empty()
        return Response(data)


class CommercialDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _bad_request("Tenant não encontrado.", "no_tenant")
        try:
            period, comparison, filters = _parse_params(request)
        except ValueError as e:
            return _bad_request(str(e))
        data = kpis.commercial_summary(tenant.id, period, comparison, filters)
        data["has_data"] = kpis.has_any_data(tenant.id)
        data["filters_applied"] = not filters.is_empty()
        return Response(data)


class OverviewView(APIView):
    """
    GET /api/dashboards/overview

    Visão Geral premium: KPIs combinados (v1 + v2) do mês atual, score de saúde,
    forecast, cards inteligentes, top categorias e principais alertas.

    Único endpoint que alimenta a Home (/app) — agrega tudo para evitar N
    chamadas no carregamento.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _bad_request("Tenant não encontrado.", "no_tenant")

        from datetime import timedelta

        from django.utils import timezone

        from .periods import Period

        # Períodos: mês corrente + 12m para tendência
        curr_month = kpis_v2.month_period()
        prev_month = kpis_v2.previous_month_period()
        today = timezone.now().date()
        last_12m = Period(start=today - timedelta(days=365), end=today)

        # KPIs do mês
        cash_in_m = kpis_v2.cash_in_period(tenant.id, curr_month)
        cash_in_p = kpis_v2.cash_in_period(tenant.id, prev_month)
        cash_out_m = kpis_v2.cash_out_period(tenant.id, curr_month)
        cash_out_p = kpis_v2.cash_out_period(tenant.id, prev_month)
        net_m = cash_in_m - cash_out_m
        net_p = cash_in_p - cash_out_p
        margin_m = kpis_v2.net_margin_pct(tenant.id, curr_month)
        margin_p = kpis_v2.net_margin_pct(tenant.id, prev_month)

        bep_info = kpis_v2.above_breakeven(tenant.id, curr_month)
        forecast = kpis_v2.cash_forecast(tenant.id, days=30)
        wc = kpis_v2.working_capital(tenant.id)
        ebitda_m = kpis_v2.ebitda(tenant.id, curr_month)
        burn = kpis_v2.burn_rate(tenant.id, months=3)

        # Top entidades (mês corrente)
        top_revenue_cats = kpis.top_categories(
            tenant.id, curr_month, direction="receivable", limit=5,
        )
        top_expense_cats = kpis.top_categories(
            tenant.id, curr_month, direction="payable", limit=5,
        )
        top_suppliers = kpis.top_financial_customers(
            tenant.id, curr_month, direction="payable", limit=5,
        )
        top_customers = kpis.top_financial_customers(
            tenant.id, curr_month, direction="receivable", limit=5,
        )

        # Séries 12 meses
        cashflow_12m = kpis.cashflow_by_month(tenant.id, last_12m)

        # Score de saúde
        health = kpis_v2.financial_health_score(tenant.id)

        # Cards inteligentes
        smart_cards = build_smart_cards(tenant.id, max_cards=6)

        return Response({
            "has_data": kpis.has_any_data(tenant.id),
            "tenant": {"id": tenant.id, "name": tenant.name, "slug": tenant.slug},
            "period": {
                "current_month": {
                    "start": curr_month.start.isoformat(),
                    "end": curr_month.end.isoformat(),
                    "label": curr_month.start.strftime("%m/%Y"),
                },
                "previous_month": {
                    "start": prev_month.start.isoformat(),
                    "end": prev_month.end.isoformat(),
                    "label": prev_month.start.strftime("%m/%Y"),
                },
            },
            "kpis": {
                "revenue_month": {
                    "current": cash_in_m,
                    "previous": cash_in_p,
                    "change_pct": _kpi_change_pct(cash_in_m, cash_in_p),
                },
                "net_profit_month": {
                    "current": net_m,
                    "previous": net_p,
                    "change_pct": _kpi_change_pct(net_m, net_p),
                },
                "net_margin_pct": {
                    "current": margin_m,
                    "previous": margin_p,
                    "change_pct": margin_m - margin_p,
                },
                "ebitda": {"current": ebitda_m},
                "cash_balance_now": {"current": kpis_v2.cash_balance(tenant.id)},
                "burn_rate_monthly": {"current": burn},
                "working_capital": wc,
                "breakeven": bep_info,
                "forecast_30d": forecast,
            },
            "growth": {
                "revenue_mom_pct": _kpi_change_pct(cash_in_m, cash_in_p),
                "profit_mom_pct": _kpi_change_pct(net_m, net_p),
            },
            "health_score": health,
            "trend_12m": cashflow_12m,
            "rankings": {
                "top_revenue_categories": top_revenue_cats,
                "top_expense_categories": top_expense_cats,
                "top_customers_receivable": top_customers,
                "top_suppliers_payable": top_suppliers,
            },
            "smart_cards": smart_cards,
        })


def _kpi_change_pct(curr: float, prev: float) -> float | None:
    if not prev:
        return None
    return (curr - prev) / abs(prev) * 100
