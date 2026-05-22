"""Testes de segurança & LGPD."""
from __future__ import annotations

import pytest
from rest_framework.exceptions import Throttled

from apps.accounts.models import Membership, User
from apps.security.models import AuditAction, AuditEntry, log_action
from apps.security.rate_limit import InMemoryRateLimiter, reset_rate_limiter


# ---------------------------------------------------------------------------
class TestRateLimiter:
    def setup_method(self):
        self.limiter = InMemoryRateLimiter()

    def test_under_limit_passes(self):
        for _ in range(5):
            self.limiter.check("k", limit=5, window_seconds=60)

    def test_over_limit_raises(self):
        for _ in range(3):
            self.limiter.check("k", limit=3, window_seconds=60)
        with pytest.raises(Throttled):
            self.limiter.check("k", limit=3, window_seconds=60)

    def test_isolated_keys(self):
        for _ in range(3):
            self.limiter.check("a", limit=3, window_seconds=60)
        # outra chave começa do zero
        self.limiter.check("b", limit=3, window_seconds=60)


@pytest.fixture(autouse=True)
def _reset_rl():
    reset_rate_limiter()
    yield
    reset_rate_limiter()


@pytest.mark.django_db
class TestAuditLog:
    def test_log_action_records(self, make_user):
        u = make_user()
        e = log_action(action=AuditAction.LOGIN, actor=u, metadata={"x": 1})
        assert e.id is not None
        assert e.action == "login"
        assert e.actor == u
        assert e.actor_email == u.email
        assert e.metadata == {"x": 1}

    def test_log_action_from_register(self, api_client):
        resp = api_client.post(
            "/api/auth/register",
            {"email": "a@b.com", "password": "StrongPass123!", "company_name": "X"},
            format="json",
        )
        assert resp.status_code == 201
        assert AuditEntry.objects.filter(action="register", actor_email="a@b.com").exists()

    def test_log_action_from_login(self, api_client, make_user):
        make_user(email="login@x.com", password="MyPass123!")
        resp = api_client.post(
            "/api/auth/login",
            {"email": "login@x.com", "password": "MyPass123!"},
            format="json",
        )
        assert resp.status_code == 200
        assert AuditEntry.objects.filter(action="login", actor_email="login@x.com").exists()


@pytest.mark.django_db
class TestLoginRateLimit:
    URL = "/api/auth/login"

    def test_blocks_after_limit(self, api_client):
        # endpoint suporta 10/60s
        for _ in range(10):
            api_client.post(self.URL, {"email": "x@x.com", "password": "wrong"}, format="json")
        resp = api_client.post(self.URL, {"email": "x@x.com", "password": "wrong"}, format="json")
        assert resp.status_code == 429


@pytest.mark.django_db
class TestExportMyData:
    URL = "/api/security/me/export"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_returns_my_data(self, authed_client):
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        d = resp.json()
        assert "user" in d
        assert d["user"]["email"] == authed_client.user.email
        assert "tenants" in d
        assert len(d["tenants"]) >= 1
        # registrou audit
        assert AuditEntry.objects.filter(
            action="data_export", actor=authed_client.user,
        ).exists()


@pytest.mark.django_db
class TestDeleteMyAccount:
    URL = "/api/security/me/delete"

    def test_requires_confirm(self, authed_client):
        resp = authed_client.post(self.URL)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "confirmation_required"

    def test_wrong_confirm_string(self, authed_client):
        resp = authed_client.post(self.URL, {"confirm": "yes"}, format="json")
        assert resp.status_code == 400

    def test_deletes_user_and_tenant_when_only_owner(self, authed_client):
        user_email = authed_client.user.email
        tenant_slug = authed_client.tenant.slug

        resp = authed_client.post(self.URL, {"confirm": "DELETAR"}, format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] is True
        assert tenant_slug in body["tenants_deleted"]

        # user e tenant removidos
        from apps.tenants.models import Tenant
        assert not User.objects.filter(email=user_email).exists()
        assert not Tenant.objects.filter(slug=tenant_slug).exists()

    def test_only_removes_membership_when_other_owner_exists(self, authed_client, make_user):
        other = make_user(email="other@x.com")
        Membership.objects.create(
            user=other, tenant=authed_client.tenant, role=Membership.Role.OWNER,
        )

        user_email = authed_client.user.email
        tenant_slug = authed_client.tenant.slug

        resp = authed_client.post(self.URL, {"confirm": "DELETAR"}, format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert tenant_slug not in body["tenants_deleted"]

        # tenant ficou
        from apps.tenants.models import Tenant
        assert Tenant.objects.filter(slug=tenant_slug).exists()
        # user removido
        assert not User.objects.filter(email=user_email).exists()


@pytest.mark.django_db
class TestAuditLogView:
    URL = "/api/security/audit-logs"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_user_sees_own_tenant_logs(self, authed_client):
        log_action(action="login", actor=authed_client.user, tenant=authed_client.tenant)
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        assert len(resp.json()["entries"]) >= 1

    def test_isolation_between_tenants(self, authed_client, make_tenant):
        other = make_tenant("other")
        log_action(action="login", tenant=other)
        log_action(action="login", tenant=authed_client.tenant)

        entries = authed_client.get(self.URL).json()["entries"]
        # só vê do próprio tenant
        slugs = {e["tenant_slug"] for e in entries}
        assert authed_client.tenant.slug in slugs
        assert other.slug not in slugs


class TestSecurityHeaders:
    def test_headers_present(self, api_client):
        resp = api_client.get("/healthz")
        assert resp["X-Content-Type-Options"] == "nosniff"
        assert resp["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in resp
        assert resp["X-Frame-Options"] == "DENY"
