"""
Helpers para resolver o tenant em DRF views.

Por que: `TenantContextMiddleware` roda antes da autenticação do DRF JWT;
em endpoints DRF, `request.tenant` ainda pode ser None mesmo com usuário
autenticado. Esta função resolve a partir de `request.user` e popula o
ContextVar para que queries posteriores funcionem corretamente.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .context import force_set_current_tenant

if TYPE_CHECKING:
    from .models import Tenant


def get_request_tenant(request) -> Tenant | None:  # type: ignore[no-untyped-def]
    """
    Resolve o tenant principal do usuário autenticado e o injeta no ContextVar.
    Retorna `None` se anônimo ou sem membership.
    """
    # Se middleware já populou (fluxo session-auth), usa
    existing = getattr(request, "tenant", None)
    if existing is not None:
        force_set_current_tenant(existing.id)
        return existing

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    membership = (
        user.memberships.select_related("tenant")
        .filter(is_active=True)
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        return None

    request.tenant = membership.tenant
    force_set_current_tenant(membership.tenant.id)
    return membership.tenant
