"""
Middleware que injeta o tenant atual no contexto a partir do usuário autenticado.

Estratégia: usuário tem `membership` ativo apontando para 1 tenant principal.
Se houver header `X-Tenant-Slug`, valida se o usuário pertence a esse tenant
e usa-o (útil para usuários multi-tenant — admins).
"""
from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from .context import set_current_tenant


class TenantContextMiddleware:
    """Define `request.tenant` e popula o ContextVar para o ciclo do request."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        tenant = self._resolve_tenant(request)
        request.tenant = tenant  # type: ignore[attr-defined]
        # Usa context manager para garantir reset mesmo em exceção
        with set_current_tenant(tenant.id if tenant else None):
            return self.get_response(request)

    @staticmethod
    def _resolve_tenant(request: HttpRequest):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        # Superusers podem trocar de tenant via header
        requested_slug = request.headers.get("X-Tenant-Slug")
        if requested_slug and user.is_superuser:
            from .models import Tenant
            try:
                return Tenant.objects.get(slug=requested_slug)  # type: ignore[no-any-return]
            except Tenant.DoesNotExist:
                return None

        # Usuário normal: tenant via membership ativo
        membership = (
            user.memberships.select_related("tenant")
            .filter(is_active=True)
            .order_by("-created_at")
            .first()
        )
        return membership.tenant if membership else None
