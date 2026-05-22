"""
Endpoints administrativos — visíveis APENAS para superuser.

Não usam multi-tenancy normal (esse view enxerga todos os tenants).
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Tenant

from . import metrics


class IsSuperuser(BasePermission):
    message = "Acesso restrito a superusuários."

    def has_permission(self, request, view):  # type: ignore[no-untyped-def]
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class SummaryView(APIView):
    permission_classes = [IsAuthenticated, IsSuperuser]

    def get(self, request: Request) -> Response:
        return Response(metrics.saas_summary())


class TenantsListView(APIView):
    permission_classes = [IsAuthenticated, IsSuperuser]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("q", "").strip()
        try:
            limit = int(request.query_params.get("limit", 50))
            limit = max(1, min(limit, 200))
        except ValueError:
            limit = 50
        return Response({
            "tenants": metrics.tenants_list(search=search, limit=limit),
            "total": Tenant.objects.count(),
        })


class TenantDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSuperuser]

    def get(self, request: Request, pk: int) -> Response:
        try:
            data = metrics.tenant_detail(int(pk))
        except Tenant.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Tenant não encontrado."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)
