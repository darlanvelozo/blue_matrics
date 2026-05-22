"""
Audit log de ações sensíveis.

Granular: cada ação tem `actor` (user), `tenant` (escopo), `action` (verbo),
`target_type/target_id` (objeto afetado), `metadata` (JSON), `ip`, `user_agent`.

Imutável — não permite update/delete via ORM normal. Use migrações de retenção.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.tenants.models import Tenant


class AuditAction(models.TextChoices):
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    REGISTER = "register", "Cadastro"
    PASSWORD_CHANGE = "password_change", "Troca de senha"
    CONTA_AZUL_CONNECT = "contaazul_connect", "Conexão Conta Azul"
    CONTA_AZUL_DISCONNECT = "contaazul_disconnect", "Desconexão Conta Azul"
    CREDENTIALS_UPDATED = "credentials_updated", "Credenciais atualizadas"
    SYNC_TRIGGERED = "sync_triggered", "Sincronização disparada"
    SUBSCRIPTION_CHECKOUT = "subscription_checkout", "Checkout iniciado"
    SUBSCRIPTION_CANCELED = "subscription_canceled", "Assinatura cancelada"
    SUBSCRIPTION_REACTIVATED = "subscription_reactivated", "Assinatura reativada"
    DATA_EXPORT = "data_export", "Exportação de dados (LGPD)"
    DATA_DELETE = "data_delete", "Exclusão de dados (LGPD)"
    ADMIN_ACCESS = "admin_access", "Acesso admin SaaS"


class AuditEntry(models.Model):
    """Entrada de auditoria. Imutável por convenção."""

    action = models.CharField(max_length=64, choices=AuditAction.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="audit_entries",
    )
    actor_email = models.EmailField(blank=True, default="")  # snapshot
    tenant = models.ForeignKey(
        Tenant, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_entries",
    )
    target_type = models.CharField(max_length=64, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]

    def __str__(self) -> str:
        who = self.actor_email or "system"
        return f"{self.created_at:%Y-%m-%d %H:%M} {who} {self.action}"


def log_action(
    *,
    action: str,
    actor=None,
    tenant=None,
    target_type: str = "",
    target_id: str | int = "",
    metadata: dict | None = None,
    request=None,
) -> AuditEntry:
    """Helper para registrar uma entrada. Extrai ip/UA do request se passado."""
    ip = None
    ua = ""
    if request is not None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = (xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")) or None
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:255]
        if actor is None and getattr(request, "user", None) and request.user.is_authenticated:
            actor = request.user
    return AuditEntry.objects.create(
        action=action,
        actor=actor,
        actor_email=getattr(actor, "email", "")[:254] if actor else "",
        tenant=tenant,
        target_type=target_type[:64],
        target_id=str(target_id)[:64],
        metadata=metadata or {},
        ip=ip,
        user_agent=ua,
    )
