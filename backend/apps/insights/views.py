"""Endpoints de Insights."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.utils import get_request_tenant

from . import llm
from .models import Insight
from .rules import generate_insights_for_tenant, materialize_insights, run_all_rules


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
    """POST → roda as regras e persiste novos insights.

    Query params:
      - enrich=true: enriquece narrativas via LLM (se INSIGHT_LLM_PROVIDER ativo).
        Cada candidato vira uma chamada à LLM; falhas mantêm a versão das regras.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrich_flag = request.query_params.get("enrich", "").lower() in ("1", "true", "yes")

        # Sem enrichment: caminho rápido
        if not enrich_flag:
            stats = generate_insights_for_tenant(tenant.id)
            return Response(
                {"stats": stats, "llm": {"requested": False, "enabled": llm.is_enabled()}},
                status=status.HTTP_202_ACCEPTED,
            )

        # Enrichment requisitado mas LLM não configurada → cair em rules-only
        if not llm.is_enabled():
            stats = generate_insights_for_tenant(tenant.id)
            return Response(
                {
                    "stats": stats,
                    "llm": {"requested": True, "enabled": False, "reason": "provider_disabled_or_missing_key"},
                },
                status=status.HTTP_202_ACCEPTED,
            )

        # Caminho com LLM: roda regras, enriquece cada candidato, persiste
        candidates = run_all_rules(tenant.id)
        snapshot = llm.build_kpis_snapshot(tenant.id)
        enriched_count = 0
        failed_count = 0
        for c in candidates:
            result = llm.enrich(c, snapshot)
            if result.enriched:
                c["title"] = result.title
                c["narrative"] = result.narrative
                c["generated_by"] = "llm"
                data = c.get("data") or {}
                data["recommendations"] = result.recommendations
                c["data"] = data
                enriched_count += 1
            else:
                failed_count += 1
        created, updated = materialize_insights(tenant.id, candidates)
        return Response(
            {
                "stats": {
                    "candidates": len(candidates),
                    "created": created,
                    "updated": updated,
                },
                "llm": {
                    "requested": True,
                    "enabled": True,
                    "enriched": enriched_count,
                    "failed": failed_count,
                },
            },
            status=status.HTTP_202_ACCEPTED,
        )


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
