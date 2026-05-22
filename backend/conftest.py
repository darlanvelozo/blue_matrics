"""Fixtures pytest compartilhadas."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Membership, User
from apps.tenants.context import set_current_tenant
from apps.tenants.models import Tenant


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def make_tenant(db):
    counter = {"n": 0}

    def _make(name: str | None = None, **kwargs) -> Tenant:
        counter["n"] += 1
        return Tenant.objects.create(
            name=name or f"Empresa {counter['n']}",
            slug=kwargs.pop("slug", f"empresa-{counter['n']}"),
            status=kwargs.pop("status", Tenant.Status.TRIAL),
            trial_ends_at=kwargs.pop(
                "trial_ends_at", timezone.now() + timedelta(days=7)
            ),
            **kwargs,
        )

    return _make


@pytest.fixture
def make_user(db):
    counter = {"n": 0}

    def _make(email: str | None = None, password: str = "test-password-123") -> User:  # noqa: S107
        counter["n"] += 1
        return User.objects.create_user(
            email=email or f"user{counter['n']}@example.com",
            password=password,
        )

    return _make


@pytest.fixture
def make_membership(db):
    def _make(user: User, tenant: Tenant, role: str = Membership.Role.OWNER) -> Membership:
        return Membership.objects.create(user=user, tenant=tenant, role=role)

    return _make


@pytest.fixture
def authed_client(api_client, make_user, make_tenant, make_membership):
    """Cliente autenticado com tenant ativo."""
    user = make_user()
    tenant = make_tenant()
    make_membership(user, tenant)
    api_client.force_authenticate(user=user)
    api_client.user = user  # atalho p/ testes
    api_client.tenant = tenant
    return api_client


@pytest.fixture
def tenant_context():
    """Context manager para forçar tenant em testes não-HTTP."""
    return set_current_tenant


# ---------------------------------------------------------------------------
# `_Widget` é um modelo dinâmico declarado em `tests/test_tenancy.py` para
# validar o manager `TenantScopedModel`. Como pytest importa todos os módulos
# de teste no collect, o model fica registrado no app cache do Django desde
# o início do run — e Django tenta cascatear DELETEs do Tenant para a tabela
# `tenants__widget` mesmo em testes que NÃO usam o fixture.
#
# Solução: criar a tabela em escopo session para garantir que ela exista
# sempre que algum Tenant for deletado em qualquer teste.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True, scope="session")
def _ensure_widget_table(django_db_setup, django_db_blocker):  # noqa: PT004
    from django.apps import apps as _apps
    from django.db import connection

    # importa o módulo para registrar o `_Widget` (no-op se já importado)
    try:
        import tests.test_tenancy  # noqa: F401
    except ImportError:
        return

    try:
        widget_model = _apps.get_model("tenants", "_Widget")
    except LookupError:
        return

    with django_db_blocker.unblock():
        with connection.schema_editor() as ed:
            try:
                ed.create_model(widget_model)
            except Exception:  # noqa: BLE001, S110
                pass  # já existe
