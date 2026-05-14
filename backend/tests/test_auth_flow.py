"""Testes do fluxo de auth: register → login → me → refresh."""
from __future__ import annotations

import pytest

from apps.accounts.models import Membership, User
from apps.tenants.models import Tenant


@pytest.mark.django_db
class TestRegister:
    URL = "/api/auth/register"

    def test_register_creates_user_tenant_membership_and_returns_tokens(self, api_client):
        payload = {
            "email": "alice@example.com",
            "password": "StrongPass123!",
            "full_name": "Alice Silva",
            "company_name": "Padaria Boa Massa",
        }
        resp = api_client.post(self.URL, payload, format="json")
        assert resp.status_code == 201, resp.content

        body = resp.json()
        assert body["user"]["email"] == "alice@example.com"
        assert body["tenant"]["name"] == "Padaria Boa Massa"
        assert body["tenant"]["slug"] == "padaria-boa-massa"
        assert body["tenant"]["status"] == "trial"
        assert "access" in body["tokens"]
        assert "refresh" in body["tokens"]

        user = User.objects.get(email="alice@example.com")
        tenant = Tenant.objects.get(slug="padaria-boa-massa")
        m = Membership.objects.get(user=user, tenant=tenant)
        assert m.role == Membership.Role.OWNER
        assert m.is_active

    def test_register_rejects_weak_password(self, api_client):
        payload = {
            "email": "bob@example.com",
            "password": "123",
            "company_name": "X",
        }
        resp = api_client.post(self.URL, payload, format="json")
        assert resp.status_code == 400

    def test_register_rejects_duplicate_email(self, api_client, make_user):
        make_user(email="dup@example.com")
        resp = api_client.post(
            self.URL,
            {"email": "dup@example.com", "password": "StrongPass123!", "company_name": "Y"},
            format="json",
        )
        assert resp.status_code == 400

    def test_register_creates_unique_slug_for_same_company_name(self, api_client):
        api_client.post(
            self.URL,
            {"email": "a@b.com", "password": "StrongPass123!", "company_name": "Cafeteria"},
            format="json",
        )
        resp = api_client.post(
            self.URL,
            {"email": "c@d.com", "password": "StrongPass123!", "company_name": "Cafeteria"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["tenant"]["slug"] == "cafeteria-2"


@pytest.mark.django_db
class TestLogin:
    URL = "/api/auth/login"

    def test_login_returns_tokens(self, api_client, make_user):
        make_user(email="login@example.com", password="MyPass123!")
        resp = api_client.post(
            self.URL,
            {"email": "login@example.com", "password": "MyPass123!"},
            format="json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access" in body["tokens"]
        assert body["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self, api_client, make_user):
        make_user(email="x@e.com", password="MyPass123!")
        resp = api_client.post(
            self.URL,
            {"email": "x@e.com", "password": "wrong"},
            format="json",
        )
        assert resp.status_code == 400

    def test_login_email_case_insensitive(self, api_client, make_user):
        make_user(email="user@example.com", password="MyPass123!")
        resp = api_client.post(
            self.URL,
            {"email": "USER@example.com", "password": "MyPass123!"},
            format="json",
        )
        assert resp.status_code == 200


@pytest.mark.django_db
class TestMe:
    URL = "/api/auth/me"

    def test_me_requires_auth(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == 401

    def test_me_returns_user_and_tenant(self, authed_client):
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == authed_client.user.email
        assert body["tenant"]["slug"] == authed_client.tenant.slug
        assert body["tenant"]["role"] == "owner"
