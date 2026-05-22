"""Endpoints de Insights."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.utils import get_request_tenant

from .models import Insight
from .rules import generate_insights_for_tenant


def _serialize(i: Insight) -> dict:
    return {
        "id": i.id,
        "kind": i.kind,
        "severity": i.severity,
        "title": i.title,
        "narrative": i.narrative,
        "data": i.data,
        "period_start": i.period_start.isoformat() if i.period_start else None,
        "period_end": i.period_end.isoformat() if i.period_end else None,
        "generated_by": i.generated_by,
        "is_read": i.is_read,
        "created_at": i.created_at.isoformat(),
    }


class ListInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Insight.unsafe_objects.filter(
            tenant_id=tenant.id,
            dismissed_at__isnull=True,
        ).order_by("-created_at")[:100]

        items = [_serialize(i) for i in qs]
        unread = sum(1 for i in items if not i["is_read"])
        return Response({"insights": items, "unread": unread, "total": len(items)})


class GenerateInsightsView(APIView):
    """POST → roda as regras e persiste novos insights."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        stats = generate_insights_for_tenant(tenant.id)
        return Response({"stats": stats}, status=status.HTTP_202_ACCEPTED)


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            insight = Insight.unsafe_objects.get(tenant_id=tenant.id, pk=pk)
        except Insight.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Insight não encontrado."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        from django.utils import timezone
        if not insight.read_at:
            insight.read_at = timezone.now()
            insight.save(update_fields=["read_at"])
        return Response(_serialize(insight))


class DismissView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            insight = Insight.unsafe_objects.get(tenant_id=tenant.id, pk=pk)
        except Insight.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Insight não encontrado."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        from django.utils import timezone
        insight.dismissed_at = timezone.now()
        insight.save(update_fields=["dismissed_at"])
        return Response({"dismissed": True})
