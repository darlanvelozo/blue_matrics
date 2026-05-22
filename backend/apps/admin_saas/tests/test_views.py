"""Testes dos endpoints de admin SaaS."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import Plan, Subscription


@pytest.fixture
def superuser(db):
    return User.objects.create_user(
        email="su@bluemetrics.app", password="StrongPass123!",
        is_staff=True, is_superuser=True,
    )


@pytest.fixture
def superuser_client(api_client, superuser):
    api_client.force_authenticate(user=superuser)
    return api_client


@pytest.mark.django_db
class TestSummaryView:
    URL = "/api/admin-saas/summary"

    def test_anonymous_denied(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_normal_user_denied(self, authed_client):
        resp = authed_client.get(self.URL)
        assert resp.status_code == 403

    def test_superuser_allowed(self, superuser_client, make_tenant):
        # cria alguns tenants + subs pra ter dados
        t1 = make_tenant("t1")
        t2 = make_tenant("t2")
        starter = Plan.objects.get(code="starter")
        growth = Plan.objects.get(code="growth")
        Subscription.objects.create(tenant=t1, plan=growth, status="active")
        Subscription.objects.create(
            tenant=t2, plan=starter, status="trialing",
            trial_ends_at=timezone.now() + timedelta(days=5),
        )
        resp = superuser_client.get(self.URL)
        assert resp.status_code == 200
        d = resp.json()
        assert d["mrr"] == 249.0
        assert d["arr"] == 249.0 * 12
        assert d["active_subscribers"] == 1
        assert d["trialing"] == 1
        assert "mrr_by_plan" in d
        assert "signups_30d" in d


@pytest.mark.django_db
class TestTenantsListView:
    URL = "/api/admin-saas/tenants"

    def test_requires_superuser(self, authed_client):
        assert authed_client.get(self.URL).status_code == 403

    def test_returns_all_tenants(self, superuser_client, make_tenant):
        make_tenant("Alpha")
        make_tenant("Beta")
        resp = superuser_client.get(self.URL)
        assert resp.status_code == 200
        d = resp.json()
        assert d["total"] >= 2
        names = [t["name"] for t in d["tenants"]]
        assert "Alpha" in names
        assert "Beta" in names

    def test_search(self, superuser_client, make_tenant):
        make_tenant("Padaria Boa Massa")
        make_tenant("Lavanderia X")
        resp = superuser_client.get(self.URL + "?q=padaria")
        assert resp.status_code == 200
        names = [t["name"].lower() for t in resp.json()["tenants"]]
        assert any("padaria" in n for n in names)
        assert not any("lavanderia" in n for n in names)


@pytest.mark.django_db
class TestTenantDetailView:
    def test_requires_superuser(self, authed_client, make_tenant):
        t = make_tenant()
        resp = authed_client.get(f"/api/admin-saas/tenants/{t.id}")
        assert resp.status_code == 403

    def test_returns_details(self, superuser_client, make_tenant):
        t = make_tenant("detail-test")
        starter = Plan.objects.get(code="starter")
        Subscription.objects.create(tenant=t, plan=starter, status="active")
        resp = superuser_client.get(f"/api/admin-saas/tenants/{t.id}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["tenant"]["slug"] == t.slug
        assert d["subscription"]["plan"] == "starter"
        assert d["subscription"]["status"] == "active"

    def test_404(self, superuser_client):
        resp = superuser_client.get("/api/admin-saas/tenants/999999")
        assert resp.status_code == 404
