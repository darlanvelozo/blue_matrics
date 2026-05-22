"""
Endpoints de LGPD: exportar dados pessoais, deletar conta.

`/api/me/export` devolve um JSON com tudo que temos do usuário e do tenant
quando ele é o owner.
`/api/me/delete` exclui a conta (e o tenant se for o único owner).
`/api/security/audit-logs` lista logs (filtrado por tenant para usuários comuns;
superuser vê tudo).
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.utils import get_request_tenant

from .models import AuditAction, AuditEntry, log_action  # noqa: F401


# ---------------------------------------------------------------------------
class ExportMyDataView(APIView):
    """Exportar dados pessoais (LGPD Art. 18)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user
        tenant = get_request_tenant(request)

        from apps.accounts.models import Membership
        from apps.billing.models import Invoice, Subscription

        memberships = Membership.objects.filter(user=user).select_related("tenant")
        subs_qs = Subscription.objects.filter(tenant__in=[m.tenant for m in memberships])
        invoices_qs = Invoice.objects.filter(tenant__in=[m.tenant for m in memberships])

        payload = {
            "exported_at": _now_iso(),
            "user": {
                "public_id": str(user.public_id),
                "email": user.email,
                "full_name": user.full_name,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
            "tenants": [
                {
                    "public_id": str(m.tenant.public_id),
                    "name": m.tenant.name,
                    "slug": m.tenant.slug,
                    "role": m.role,
                    "joined_at": m.created_at.isoformat(),
                }
                for m in memberships
            ],
            "subscriptions": [
                {
                    "tenant_slug": s.tenant.slug,
                    "plan": s.plan.code,
                    "status": s.status,
                    "trial_ends_at": s.trial_ends_at.isoformat() if s.trial_ends_at else None,
                    "current_period_end": (
                        s.current_period_end.isoformat() if s.current_period_end else None
                    ),
                }
                for s in subs_qs.select_related("plan", "tenant")
            ],
            "invoices": [
                {
                    "tenant_slug": i.tenant.slug,
                    "amount": float(i.amount),
                    "currency": i.currency,
                    "status": i.status,
                    "created_at": i.created_at.isoformat(),
                }
                for i in invoices_qs.select_related("tenant")
            ],
        }

        log_action(
            action=AuditAction.DATA_EXPORT,
            actor=user,
            tenant=tenant,
            metadata={"records": len(memberships) + invoices_qs.count() + subs_qs.count()},
            request=request,
        )
        return Response(payload)


class DeleteMyAccountView(APIView):
    """
    Exclusão da conta (LGPD Art. 18 V).

    Regras:
    - Owner único do tenant → exclui tenant inteiro (cascateia)
    - Membro/owner não-único → apenas remove membership e desativa user
    - Body opcional: `{ "confirm": "DELETAR" }` (string-bloqueio explícito)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        confirm = (request.data.get("confirm") or "").upper().strip()
        if confirm != "DELETAR":
            return Response(
                {"error": {
                    "code": "confirmation_required",
                    "message": "Para confirmar, envie {\"confirm\": \"DELETAR\"}.",
                }},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        tenant = get_request_tenant(request)
        deleted_tenants: list[str] = []

        from apps.accounts.models import Membership
        from apps.tenants.models import Tenant

        # Para cada membership do usuário: se ele é o único owner, deleta o tenant.
        for m in Membership.objects.filter(user=user).select_related("tenant"):
            t: Tenant = m.tenant
            other_owners = Membership.objects.filter(
                tenant=t, role=Membership.Role.OWNER, is_active=True,
            ).exclude(user=user).exists()
            if not other_owners:
                deleted_tenants.append(t.slug)
                # Quebra FKs de audit entries para preservar histórico de auditoria
                AuditEntry.objects.filter(tenant=t).update(tenant=None)
                t.delete()  # cascateia memberships, sales, etc.
            else:
                m.delete()

        # Audita ANTES de deletar o user — não referencia tenant FK pois
        # ele pode ter sido deletado (snapshot em metadata).
        log_action(
            action=AuditAction.DATA_DELETE,
            actor=user,
            tenant=None,
            metadata={
                "user_email": user.email,
                "deleted_tenants": deleted_tenants,
                "tenant_slug": tenant.slug if tenant else None,
            },
            request=request,
        )

        user_email = user.email
        user.delete()

        return Response({
            "deleted": True,
            "user_email": user_email,
            "tenants_deleted": deleted_tenants,
        })


class AuditLogView(APIView):
    """
    GET /api/security/audit-logs

    - Usuário comum: vê logs do seu tenant (últimos 200).
    - Superuser: pode passar `?tenant=<slug>` ou `?all=1`.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user
        qs = AuditEntry.objects.all()

        if user.is_superuser:
            slug = request.query_params.get("tenant", "").strip()
            show_all = request.query_params.get("all", "").strip() == "1"
            if slug:
                qs = qs.filter(tenant__slug=slug)
            elif not show_all:
                qs = qs.filter(actor=user)
        else:
            tenant = get_request_tenant(request)
            if tenant is None:
                return Response(
                    {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(tenant=tenant)

        entries = qs.select_related("actor", "tenant").order_by("-created_at")[:200]
        return Response({
            "entries": [
                {
                    "id": e.id,
                    "action": e.action,
                    "actor_email": e.actor_email,
                    "tenant_slug": e.tenant.slug if e.tenant else None,
                    "target_type": e.target_type,
                    "target_id": e.target_id,
                    "metadata": e.metadata,
                    "ip": e.ip,
                    "created_at": e.created_at.isoformat(),
                }
                for e in entries
            ]
        })


def _now_iso() -> str:
    from django.utils import timezone
    return timezone.now().isoformat()
