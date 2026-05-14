"""Endpoints de dashboards."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.utils import get_request_tenant

from . import kpis
from .periods import resolve_period


def _bad_request(message: str, code: str = "invalid_request") -> Response:
    return Response(
        {"error": {"code": code, "message": message}},
        status=status.HTTP_400_BAD_REQUEST,
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
    return period, comparison


class ExecutiveDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _bad_request("Tenant não encontrado.", "no_tenant")
        try:
            period, comparison = _parse_params(request)
        except ValueError as e:
            return _bad_request(str(e))
        data = kpis.executive_summary(tenant.id, period, comparison)
        data["has_data"] = kpis.has_any_data(tenant.id)
        return Response(data)


class FinancialDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _bad_request("Tenant não encontrado.", "no_tenant")
        try:
            period, comparison = _parse_params(request)
        except ValueError as e:
            return _bad_request(str(e))
        data = kpis.financial_summary(tenant.id, period, comparison)
        data["has_data"] = kpis.has_any_data(tenant.id)
        return Response(data)


class CommercialDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _bad_request("Tenant não encontrado.", "no_tenant")
        try:
            period, comparison = _parse_params(request)
        except ValueError as e:
            return _bad_request(str(e))
        data = kpis.commercial_summary(tenant.id, period, comparison)
        data["has_data"] = kpis.has_any_data(tenant.id)
        return Response(data)
