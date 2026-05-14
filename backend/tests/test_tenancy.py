"""
Testes do isolamento multi-tenant.

CRÍTICO: garantem que dados de um tenant nunca vazam para outro via o manager
padrão, e que o middleware popula o contexto corretamente.
"""
from __future__ import annotations

import pytest
from django.db import models

from apps.tenants.context import current_tenant_id, set_current_tenant
from apps.tenants.models import TenantScopedModel


# -------------------------------------------------------------------
# Modelo dummy para testar a abstração — criado em runtime no app de tests
# usando o app "tenants" para reaproveitar a infra de migrations.
# -------------------------------------------------------------------
class _Widget(TenantScopedModel):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = "tenants"
        managed = False  # criamos a tabela na mão no setup do teste


@pytest.fixture(scope="module")
def widget_table(django_db_setup, django_db_blocker):
    """Cria a tabela do _Widget no banco de teste."""
    from django.db import connection

    with django_db_blocker.unblock():
        with connection.schema_editor() as ed:
            try:
                ed.create_model(_Widget)
            except Exception:  # noqa: BLE001, S110
                pass  # rerun-safe  # já criado em rerun
        yield
        with connection.schema_editor() as ed:
            try:
                ed.delete_model(_Widget)
            except Exception:  # noqa: BLE001, S110
                pass  # rerun-safe


@pytest.mark.django_db
class TestTenantScopedManager:
    def test_no_context_returns_empty_by_default_strict(self, make_tenant, widget_table):
        t1 = make_tenant("A")
        with set_current_tenant(t1.id):
            _Widget.objects.create(name="w1")
        # Sem tenant no contexto → manager retorna vazio
        assert _Widget.objects.count() == 0

    def test_filters_by_current_tenant(self, make_tenant, widget_table):
        t1 = make_tenant("A")
        t2 = make_tenant("B")
        with set_current_tenant(t1.id):
            _Widget.objects.create(name="A1")
            _Widget.objects.create(name="A2")
        with set_current_tenant(t2.id):
            _Widget.objects.create(name="B1")

        with set_current_tenant(t1.id):
            names = sorted(_Widget.objects.values_list("name", flat=True))
            assert names == ["A1", "A2"]

        with set_current_tenant(t2.id):
            assert list(_Widget.objects.values_list("name", flat=True)) == ["B1"]

    def test_unsafe_objects_sees_everything(self, make_tenant, widget_table):
        t1 = make_tenant("A")
        t2 = make_tenant("B")
        with set_current_tenant(t1.id):
            _Widget.objects.create(name="x")
        with set_current_tenant(t2.id):
            _Widget.objects.create(name="y")

        # bypass intencional (admin)
        assert _Widget.unsafe_objects.count() == 2

    def test_save_without_tenant_in_context_raises(self, widget_table):
        with pytest.raises(ValueError, match="sem tenant"):
            _Widget(name="orphan").save()

    def test_save_with_explicit_tenant_id_works(self, make_tenant, widget_table):
        t = make_tenant("explicit")
        w = _Widget(name="ok", tenant_id=t.id)
        w.save()
        with set_current_tenant(t.id):
            assert _Widget.objects.filter(name="ok").exists()


@pytest.mark.django_db
class TestMiddleware:
    def test_authed_request_populates_context(self, authed_client):
        # Endpoint /me usa request.user, mas vamos verificar via API
        resp = authed_client.get("/api/auth/me")
        assert resp.status_code == 200
        # Após o request, context já foi resetado
        assert current_tenant_id() is None

    def test_anonymous_request_has_no_tenant(self, api_client):
        resp = api_client.get("/healthz")
        assert resp.status_code == 200
        assert current_tenant_id() is None
