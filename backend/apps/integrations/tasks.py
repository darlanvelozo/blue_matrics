"""
Tasks Celery — refresh proativo de tokens prestes a expirar.

Em dev local, Celery roda em eager. Em prod, beat schedule chama a cada 5min.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import ContaAzulConnection
from .services import ContaAzulOAuthService, OAuthError

logger = logging.getLogger(__name__)


@shared_task(name="integrations.refresh_expiring_tokens")
def refresh_expiring_tokens(window_minutes: int = 10) -> dict[str, int]:
    """
    Renova access tokens que expiram nos próximos `window_minutes`.
    Retorna estatísticas {checked, refreshed, failed}.
    """
    horizon = timezone.now() + timedelta(minutes=window_minutes)

    qs = ContaAzulConnection.objects.unsafe_objects.filter(  # type: ignore[attr-defined]
        status=ContaAzulConnection.Status.CONNECTED,
        expires_at__lte=horizon,
    ) if hasattr(ContaAzulConnection.objects, "unsafe_objects") else (
        ContaAzulConnection.objects.filter(
            status=ContaAzulConnection.Status.CONNECTED,
            expires_at__lte=horizon,
        )
    )
    # ContaAzulConnection não é TenantScopedModel, então `.objects` é o manager
    # padrão sem filtro por tenant. Mas usamos OneToOne para Tenant, o que
    # é seguro: cada row pertence a 1 tenant via FK.

    stats = {"checked": 0, "refreshed": 0, "failed": 0}

    for conn in qs.iterator():
        stats["checked"] += 1
        if not conn.refresh_token_enc:
            conn.mark_error("Sem refresh_token; reautenticação necessária.")
            conn.save(update_fields=["status", "last_error", "updated_at"])
            stats["failed"] += 1
            continue
        service = ContaAzulOAuthService.for_connection(conn)
        try:
            new_tokens = service.refresh(conn.refresh_token)
        except OAuthError as e:
            logger.warning("refresh falhou tenant=%s err=%s", conn.tenant_id, e)
            conn.mark_error(str(e))
            conn.save(update_fields=["status", "last_error", "updated_at"])
            stats["failed"] += 1
            continue

        conn.set_access_token(new_tokens.access_token, expires_in=new_tokens.expires_in)
        if new_tokens.refresh_token:
            conn.set_refresh_token(new_tokens.refresh_token)
        conn.mark_connected()
        conn.save()
        stats["refreshed"] += 1

    return stats
