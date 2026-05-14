"""
Manager tenant-aware. Filtra automaticamente queries por `tenant_id` lido do
context var. Se nenhum tenant estiver definido (ex: request anônimo ou shell),
o comportamento depende da flag `strict`:

- strict=True (padrão): retorna queryset vazio (fail-closed)
- strict=False: retorna queryset completo (uso em superuser / scripts)

Para escapes legítimos, use `Model.unsafe_objects`.
"""
from __future__ import annotations

from django.db import models
from django.db.models import QuerySet

from .context import current_tenant_id


class TenantScopedQuerySet(QuerySet):
    """QuerySet que carrega flag para auditoria."""

    pass


class TenantScopedManager(models.Manager):
    """Manager que aplica filtro automático por tenant."""

    use_in_migrations = True

    def __init__(self, strict: bool = True) -> None:
        super().__init__()
        self._strict = strict

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        tenant_id = current_tenant_id()
        if tenant_id is None:
            if self._strict:
                # fail-closed: sem tenant no contexto, ninguém vê nada
                return qs.none()
            return qs
        return qs.filter(tenant_id=tenant_id)


class UnscopedManager(models.Manager):
    """Manager bruto sem filtro. Use apenas em código admin/sistema."""

    use_in_migrations = True
