"""
Tenant context vars — propaga o tenant atual em qualquer ponto do request,
inclusive em tasks Celery e managers.

Uso:
    from apps.tenants.context import current_tenant_id, set_current_tenant

    with set_current_tenant(tenant.id):
        # qualquer query tenant-scoped filtra automaticamente
        ...
"""
from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

_current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)


def current_tenant_id() -> int | None:
    return _current_tenant_id.get()


@contextmanager
def set_current_tenant(tenant_id: int | None) -> Generator[None, None, None]:
    token = _current_tenant_id.set(tenant_id)
    try:
        yield
    finally:
        _current_tenant_id.reset(token)


def force_set_current_tenant(tenant_id: int | None) -> None:
    """
    Define o tenant sem context manager (uso em middleware).
    Limpar manualmente em request_finished se necessário.
    """
    _current_tenant_id.set(tenant_id)
