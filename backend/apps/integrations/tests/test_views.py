"""Testes dos endpoints OAuth (authorize, callback, status, disconnect)."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.integrations.models import ContaAzulConnection, OAuthState
from apps.integrations.services import OAuthError, OAuthTokens

VALID_CFG = {
    "CLIENT_ID": "test-client",
    "CLIENT_SECRET": "test-secret",
    "REDIRECT_URI": "http://localhost:8000/api/integrations/contaazul/callback",
    "AUTH_URL": "https://auth.contaazul.com/oauth2/authorize",
    "TOKEN_URL": "https://auth.contaazul.com/oauth2/token",
    "API_BASE": "https://api-v2.contaazul.com/v1",
    "SCOPE": "openid profile aws.cognito.signin.user.admin",
}


@pytest.fixture(autouse=True)
def _configured(settings):
    settings.CONTA_AZUL = VALID_CFG
    settings.FRONTEND_URL = "http://localhost:3000"


@pytest.mark.django_db
class TestStatusView:
    URL = "/api/integrations/contaazul/status"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_returns_disconnected_for_new_tenant(self, authed_client):
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()["status"] == "disconnected"

    def test_does_not_leak_tokens(self, authed_client):
        conn = ContaAzulConnection.objects.create(tenant=authed_client.tenant)
        conn.set_access_token("super-secret-access")
        conn.set_refresh_token("super-secret-refresh")
        conn.mark_connected()
        conn.save()

        body = authed_client.get(self.URL).json()
        text = str(body)
        assert "super-secret-access" not in text
        assert "super-secret-refresh" not in text
        assert "access_token" not in body
        assert body["status"] == "connected"


@pytest.mark.django_db
class TestAuthorizeView:
    URL = "/api/integrations/contaazul/authorize"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_returns_url_with_state_and_persists(self, authed_client):
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        body = resp.json()
        assert "url" in body
        assert body["url"].startswith("https://auth.contaazul.com/oauth2/authorize")
        assert "state" in body
        assert OAuthState.objects.filter(
            state=body["state"], tenant=authed_client.tenant
        ).exists()

    def test_returns_503_when_misconfigured(self, authed_client, settings):
        settings.CONTA_AZUL = {**VALID_CFG, "CLIENT_ID": ""}
        resp = authed_client.get(self.URL)
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "oauth_misconfigured"


@pytest.mark.django_db
class TestCallbackView:
    URL = "/api/integrations/contaazul/callback"

    def test_redirects_with_error_when_missing_params(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == 302
        assert "status=error" in resp["Location"]
        assert "missing_code_or_state" in resp["Location"]

    def test_provider_error_propagates(self, api_client):
        resp = api_client.get(f"{self.URL}?error=access_denied")
        assert resp.status_code == 302
        assert "access_denied" in resp["Location"]

    def test_invalid_state(self, api_client):
        resp = api_client.get(f"{self.URL}?code=x&state=does-not-exist")
        assert resp.status_code == 302
        assert "invalid_state" in resp["Location"]

    def test_expired_state(self, api_client, make_tenant):
        t = make_tenant()
        st = OAuthState.objects.create(state="abc", tenant=t)
        st.created_at = timezone.now() - timedelta(minutes=20)
        st.save()
        resp = api_client.get(f"{self.URL}?code=c&state=abc")
        assert resp.status_code == 302
        assert "state_expired_or_used" in resp["Location"]

    @patch("apps.integrations.views.ContaAzulOAuthService.exchange_code")
    def test_happy_path_stores_tokens_and_redirects(
        self, mock_exchange, api_client, make_tenant
    ):
        mock_exchange.return_value = OAuthTokens(
            access_token="ACC-1",
            refresh_token="REF-1",
            expires_in=3600,
            scope="openid",
        )
        t = make_tenant()
        OAuthState.objects.create(state="ok-state", tenant=t)

        resp = api_client.get(f"{self.URL}?code=valid-code&state=ok-state")
        assert resp.status_code == 302
        assert "status=connected" in resp["Location"]

        conn = ContaAzulConnection.objects.get(tenant=t)
        assert conn.status == ContaAzulConnection.Status.CONNECTED
        assert conn.access_token == "ACC-1"
        assert conn.refresh_token == "REF-1"
        assert conn.expires_at is not None

        st = OAuthState.objects.get(state="ok-state")
        assert st.consumed_at is not None

    @patch("apps.integrations.views.ContaAzulOAuthService.exchange_code")
    def test_exchange_failure_marks_error(self, mock_exchange, api_client, make_tenant):
        mock_exchange.side_effect = OAuthError("400 bad code")
        t = make_tenant()
        OAuthState.objects.create(state="fail-state", tenant=t)

        resp = api_client.get(f"{self.URL}?code=x&state=fail-state")
        assert resp.status_code == 302
        assert "token_exchange_failed" in resp["Location"]
        conn = ContaAzulConnection.objects.get(tenant=t)
        assert conn.status == ContaAzulConnection.Status.ERROR
        assert "400" in conn.last_error


@pytest.mark.django_db
class TestDisconnectView:
    URL = "/api/integrations/contaazul/disconnect"

    def test_requires_auth(self, api_client):
        assert api_client.post(self.URL).status_code == 401

    def test_clears_tokens(self, authed_client):
        conn = ContaAzulConnection.objects.create(tenant=authed_client.tenant)
        conn.set_access_token("x")
        conn.set_refresh_token("y")
        conn.mark_connected()
        conn.save()

        resp = authed_client.post(self.URL)
        assert resp.status_code == 200
        conn.refresh_from_db()
        assert conn.status == ContaAzulConnection.Status.DISCONNECTED
        assert conn.access_token_enc == ""
        assert conn.refresh_token_enc == ""
        assert conn.expires_at is None

    def test_disconnect_without_existing_connection(self, authed_client):
        resp = authed_client.post(self.URL)
        assert resp.status_code == 200
        assert resp.json()["status"] == "disconnected"
