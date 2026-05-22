"""Endpoints de sync — listar logs, disparar sync."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integrations.models import ContaAzulConnection
from apps.tenants.utils import get_request_tenant

from .models import SyncLog
from .tasks import sync_tenant_task


def _serialize_log(log: SyncLog) -> dict:
    return {
        "id": log.id,
        "resource": log.resource or "all",
        "status": log.status,
        "started_at": log.started_at.isoformat(),
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
        "fetched": log.fetched,
        "upserted": log.upserted,
        "errors": log.errors,
        "message": log.message,
    }


class LogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = SyncLog.objects.filter(tenant_id=tenant.id).order_by("-started_at")[:50]
        return Response({"logs": [_serialize_log(log) for log in qs]})


class RunNowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            conn = ContaAzulConnection.objects.get(tenant_id=tenant.id)
        except ContaAzulConnection.DoesNotExist:
            return Response(
                {"error": {"code": "not_connected", "message": "Conecte a Conta Azul primeiro."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if conn.status != ContaAzulConnection.Status.CONNECTED:
            return Response(
                {
                    "error": {
                        "code": "not_connected",
                        "message": "Conexão não está ativa. Reconecte sua Conta Azul.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Em dev (eager mode) executa síncrono via .apply(); em prod cai na fila via .delay().
        from django.conf import settings as dj_settings
        if getattr(dj_settings, "CELERY_TASK_ALWAYS_EAGER", False):
            async_result = sync_tenant_task.apply(args=[tenant.id])
            return Response(
                {"task_id": str(async_result.id), "status": "done"},
                status=status.HTTP_202_ACCEPTED,
            )
        async_result = sync_tenant_task.delay(tenant.id)
        return Response(
            {"task_id": str(async_result.id), "status": "queued"},
            status=status.HTTP_202_ACCEPTED,
        )
