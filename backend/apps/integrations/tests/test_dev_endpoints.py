"""Testes de endpoints para apps dev: exchange-code e manual-token."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.integrations.models import ContaAzulConnection
from apps.integrations.services import OAuthError, OAuthTokens

VALID_CFG = {
    "CLIENT_ID": "",
    "CLIENT_SECRET": "",
    "REDIRECT_URI": "http://localhost:8000/api/integrations/contaazul/callback",
    "AUTH_URL": "https://auth.contaazul.com/oauth2/authorize",
    "TOKEN_URL": "https://auth.contaazul.com/oauth2/token",
    "API_BASE": "https://api-v2.contaazul.com/v1",
    "SCOPE": "openid profile aws.cognito.signin.user.admin",
}


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.CONTA_AZUL = VALID_CFG
    settings.FRONTEND_URL = "http://localhost:3000"


@pytest.mark.django_db
class TestExchangeCode:
    URL = "/api/integrations/contaazul/exchange-code"

    def test_requires_auth(self, api_client):
        assert api_client.post(self.URL, {"code": "x"}, format="json").status_code == 401

    def test_400_missing_code(self, authed_client):
        # tem creds
        conn = ContaAzulConnection.objects.create(
            tenant=authed_client.tenant, client_id="cid"
        )
        conn.set_client_secret("csec")
        conn.save()
        resp = authed_client.post(self.URL, {}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "missing_code"

    def test_400_no_credentials(self, authed_client):
        resp = authed_client.post(self.URL, {"code": "abc"}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "no_credentials"

    @patch("apps.integrations.views.ContaAzulOAuthService.exchange_code")
    def test_happy_path_stores_tokens(self, mock_exchange, authed_client):
        conn = ContaAzulConnection.objects.create(
            tenant=authed_client.tenant,
            client_id="cid",
            redirect_uri_override="https://contaazul.com",
        )
        conn.set_client_secret("csec")
        conn.save()

        mock_exchange.return_value = OAuthTokens(
            access_token="ACC", refresh_token="REF",
            expires_in=3600, scope="openid",
        )
        resp = authed_client.post(self.URL, {"code": "valid"}, format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "connected"
        assert body["dev_mode"] is True

        conn.refresh_from_db()
        assert conn.access_token == "ACC"
        assert conn.refresh_token == "REF"

    @patch("apps.integrations.views.ContaAzulOAuthService.exchange_code")
    def test_failure_marks_error(self, mock_exchange, authed_client):
        conn = ContaAzulConnection.objects.create(
            tenant=authed_client.tenant, client_id="cid"
        )
        conn.set_client_secret("csec")
        conn.save()
        mock_exchange.side_effect = OAuthError("invalid_grant")

        resp = authed_client.post(self.URL, {"code": "bad"}, format="json")
        assert resp.status_code == 400
        assert "invalid_grant" in resp.json()["error"]["message"]


@pytest.mark.django_db
class TestManualToken:
    URL = "/api/integrations/contaazul/manual-token"

    def test_requires_auth(self, api_client):
        assert api_client.post(self.URL, {"access_token": "x"}, format="json").status_code == 401

    def test_400_missing_access_token(self, authed_client):
        resp = authed_client.post(self.URL, {}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "missing_access_token"

    def test_stores_token_and_marks_connected(self, authed_client):
        resp = authed_client.post(
            self.URL,
            {"access_token": "my-token", "expires_in": 1800, "scope": "openid"},
            format="json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "connected"
        assert body["scope"] == "openid"

        conn = ContaAzulConnection.objects.get(tenant=authed_client.tenant)
        assert conn.access_token == "my-token"

    def test_stores_refresh_token_optionally(self, authed_client):
        resp = authed_client.post(
            self.URL,
            {"access_token": "a", "refresh_token": "r"},
            format="json",
        )
        assert resp.status_code == 200
        conn = ContaAzulConnection.objects.get(tenant=authed_client.tenant)
        assert conn.refresh_token == "r"


@pytest.mark.django_db
class TestCredentialsWithOverrides:
    URL = "/api/integrations/contaazul/credentials"

    def test_saves_overrides(self, authed_client):
        resp = authed_client.put(
            self.URL,
            {
                "client_id": "cid",
                "client_secret": "csec",
                "redirect_uri_override": "https://contaazul.com",
                "auth_url_override": "https://auth.contaazul.com/login",
            },
            format="json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["dev_mode"] is True
        assert body["redirect_uri"] == "https://contaazul.com"

        conn = ContaAzulConnection.objects.get(tenant=authed_client.tenant)
        assert conn.redirect_uri_override == "https://contaazul.com"
        assert conn.auth_url_override == "https://auth.contaazul.com/login"

    def test_authorize_uses_overrides(self, authed_client):
        # cadastra com overrides
        authed_client.put(
            self.URL,
            {
                "client_id": "cid",
                "client_secret": "csec",
                "redirect_uri_override": "https://contaazul.com",
                "auth_url_override": "https://auth.contaazul.com/login",
            },
            format="json",
        )
        resp = authed_client.get("/api/integrations/contaazul/authorize")
        assert resp.status_code == 200
        url = resp.json()["url"]
        # auth_url override aplicado
        assert url.startswith("https://auth.contaazul.com/login")
        # redirect_uri override aplicado (url-encoded)
        assert "redirect_uri=https%3A%2F%2Fcontaazul.com" in url
