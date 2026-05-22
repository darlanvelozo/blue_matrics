"""
Endpoints de relatórios:
- Exportação Excel/HTML
- Criação/listagem/revogação de links públicos
- Endpoint público para visualizar via token
"""
from __future__ import annotations

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics import kpis
from apps.analytics.periods import resolve_period
from apps.tenants.utils import get_request_tenant

from . import exporters
from .models import SharedReport

DASHBOARD_KINDS = ("executive", "financial", "commercial")


def _no_tenant():
    return Response(
        {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _compute_dashboard(tenant_id: int, dashboard: str, preset: str = "last_12m") -> dict:
    period = resolve_period(preset=preset)
    if dashboard == "executive":
        return kpis.executive_summary(tenant_id, period)
    if dashboard == "financial":
        return kpis.financial_summary(tenant_id, period)
    if dashboard == "commercial":
        return kpis.commercial_summary(tenant_id, period)
    raise ValueError(f"Dashboard inválido: {dashboard}")


# ---------------------------------------------------------------------------
class ExportView(APIView):
    """
    GET /api/reports/export/<dashboard>/<fmt>
        fmt: excel | html
        ?preset=last_12m (opcional)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, dashboard: str, fmt: str) -> HttpResponse:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant()  # type: ignore[return-value]
        if dashboard not in DASHBOARD_KINDS:
            return Response(
                {"error": {"code": "invalid_dashboard", "message": "dashboard inválido."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        preset = request.query_params.get("preset", "last_12m")
        data = _compute_dashboard(tenant.id, dashboard, preset)

        ts = timezone.now().strftime("%Y%m%d-%H%M")
        slug = tenant.slug
        if fmt == "excel":
            fn = {
                "executive": exporters.executive_to_excel,
                "financial": exporters.financial_to_excel,
                "commercial": exporters.commercial_to_excel,
            }[dashboard]
            content = fn(data, tenant.name)
            resp = HttpResponse(
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            resp["Content-Disposition"] = (
                f'attachment; filename="bluemetrics-{dashboard}-{slug}-{ts}.xlsx"'
            )
            return resp
        if fmt == "html":
            fn_html = {
                "executive": exporters.executive_to_html,
                "financial": exporters.financial_to_html,
                "commercial": exporters.commercial_to_html,
            }[dashboard]
            html = fn_html(data, tenant.name)
            resp = HttpResponse(html, content_type="text/html; charset=utf-8")
            # Sem "attachment" — abre no browser, usuário clica em "Imprimir → PDF"
            return resp
        return Response(
            {"error": {"code": "invalid_format", "message": "Use fmt=excel ou html."}},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ---------------------------------------------------------------------------
class SharesListView(APIView):
    """GET (lista) / POST (cria)"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant()
        qs = SharedReport.unsafe_objects.filter(tenant_id=tenant.id).order_by("-created_at")[:50]
        return Response({
            "shares": [_serialize(s) for s in qs],
        })

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant()
        dashboard = (request.data.get("dashboard") or "").strip()
        if dashboard not in DASHBOARD_KINDS:
            return Response(
                {"error": {"code": "invalid_dashboard", "message": "dashboard inválido."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        preset = (request.data.get("preset") or "last_12m").strip()
        try:
            days_valid = int(request.data.get("days_valid", 7))
            days_valid = max(1, min(days_valid, 90))
        except (TypeError, ValueError):
            days_valid = 7

        share = SharedReport.create_share(
            tenant=tenant, dashboard=dashboard, preset=preset,
            days_valid=days_valid,
            created_by_email=getattr(request.user, "email", ""),
        )
        return Response(_serialize(share), status=status.HTTP_201_CREATED)


class ShareDetailView(APIView):
    """DELETE (revoga)"""

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, pk: int) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant()
        try:
            s = SharedReport.unsafe_objects.get(tenant_id=tenant.id, id=pk)
        except SharedReport.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Share não encontrado."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        s.revoked_at = timezone.now()
        s.save(update_fields=["revoked_at"])
        return Response(_serialize(s))


class PublicShareView(APIView):
    """
    GET /r/<token>  — público, sem auth.
    Retorna o HTML imprimível direto pra ser aberto no browser.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request: Request, token: str) -> HttpResponse:
        try:
            share = SharedReport.unsafe_objects.select_related("tenant").get(token=token)
        except SharedReport.DoesNotExist:
            return HttpResponse(_html_error("Link inválido"), status=404, content_type="text/html")
        if not share.is_active():
            reason = "Link expirado" if share.revoked_at is None else "Link revogado"
            return HttpResponse(
                _html_error(reason),
                status=410, content_type="text/html",
            )

        # incrementa view_count (sem race-condition crítica em sqlite — basta atomic)
        SharedReport.unsafe_objects.filter(id=share.id).update(view_count=share.view_count + 1)

        data = _compute_dashboard(share.tenant_id, share.dashboard, share.preset)
        fn_html = {
            "executive": exporters.executive_to_html,
            "financial": exporters.financial_to_html,
            "commercial": exporters.commercial_to_html,
        }[share.dashboard]
        html = fn_html(data, share.tenant.name)
        # remove o botão "Imprimir / Salvar como PDF"? Não — deixar para o leitor poder gerar PDF
        return HttpResponse(html, content_type="text/html; charset=utf-8")


# ---------------------------------------------------------------------------
def _serialize(s: SharedReport) -> dict:
    return {
        "id": s.id,
        "dashboard": s.dashboard,
        "preset": s.preset,
        "token": s.token,
        "url_path": f"/r/{s.token}",
        "expires_at": s.expires_at.isoformat(),
        "revoked_at": s.revoked_at.isoformat() if s.revoked_at else None,
        "view_count": s.view_count,
        "is_active": s.is_active(),
        "created_at": s.created_at.isoformat(),
        "created_by_email": s.created_by_email,
    }


def _html_error(message: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"/>
<title>BlueMetrics — {message}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; display: flex; align-items: center;
         justify-content: center; min-height: 100vh; margin: 0; color: #0a0a0a; }}
  .card {{ text-align: center; padding: 48px; }}
  h1 {{ font-size: 28px; margin-bottom: 8px; }}
  p {{ color: #6b7280; }}
</style>
</head><body><div class="card">
  <h1>{message}</h1>
  <p>Esse relatório não está mais disponível. Solicite um novo link ao remetente.</p>
</div></body></html>"""
