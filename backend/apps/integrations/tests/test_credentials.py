"""Testes do endpoint /credentials (BYO credentials por tenant)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.integrations.models import ContaAzulConnection
from apps.integrations.services import OAuthTokens


@pytest.fixture(autouse=True)
def _configured(settings):
    # Sem CLIENT_ID/SECRET no settings: força uso das credenciais do tenant
    settings.CONTA_AZUL = {
        "CLIENT_ID": "",
        "CLIENT_SECRET": "",
        "REDIRECT_URI": "http://localhost:8000/api/integrations/contaazul/callback",
        "AUTH_URL": "https://auth.contaazul.com/oauth2/authorize",
        "TOKEN_URL": "https://auth.contaazul.com/oauth2/token",
        "API_BASE": "https://api-v2.contaazul.com/v1",
        "SCOPE": "openid profile aws.cognito.signin.user.admin",
    }
    settings.FRONTEND_URL = "http://localhost:3000"


URL = "/api/integrations/contaazul/credentials"


@pytest.mark.django_db
class TestCredentialsGet:
    def test_requires_auth(self, api_client):
        assert api_client.get(URL).status_code == 401

    def test_returns_empty_for_new_tenant(self, authed_client):
        resp = authed_client.get(URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_credentials"] is False
        assert body["client_id"] == ""
        assert body["redirect_uri"].endswith("/callback")

    def test_returns_client_id_but_not_secret(self, authed_client):
        conn = ContaAzulConnection.objects.create(
            tenant=authed_client.tenant,
            client_id="my-app-id",
        )
        conn.set_client_secret("super-secret-value")
        conn.save()

        body = authed_client.get(URL).json()
        assert body["client_id"] == "my-app-id"
        assert body["has_credentials"] is True
        # secret nunca exposto
        text = str(body)
        assert "super-secret-value" not in text
        assert "client_secret" not in body


@pytest.mark.django_db
class TestCredentialsPut:
    def test_requires_auth(self, api_client):
        assert api_client.put(URL, {}, format="json").status_code == 401

    def test_saves_credentials(self, authed_client):
        resp = authed_client.put(
            URL,
            {"client_id": "abc123", "client_secret": "xyz789"},
            format="json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["client_id"] == "abc123"
        assert body["has_credentials"] is True

        conn = ContaAzulConnection.objects.get(tenant=authed_client.tenant)
        assert conn.client_id == "abc123"
        assert conn.client_secret == "xyz789"  # decifra
        # secret é criptografado em repouso
        assert "xyz789" not in conn.client_secret_enc

    def test_rejects_missing_fields(self, authed_client):
        resp = authed_client.put(URL, {"client_id": "only-id"}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "missing_fields"

    def test_rejects_too_long(self, authed_client):
        resp = authed_client.put(
            URL,
            {"client_id": "x" * 300, "client_secret": "y"},
            format="json",
        )
        assert resp.status_code == 400

    def test_rotating_credentials_revokes_existing_connection(self, authed_client):
        conn = ContaAzulConnection.objects.create(
            tenant=authed_client.tenant,
            client_id="old-id",
        )
        conn.set_client_secret("old-secret")
        conn.set_access_token("acc", expires_in=3600)
        conn.set_refresh_token("ref")
        conn.mark_connected()
        conn.save()

        resp = authed_client.put(
            URL,
            {"client_id": "new-id", "client_secret": "new-secret"},
            format="json",
        )
        assert resp.status_code == 200
        conn.refresh_from_db()
        assert conn.client_id == "new-id"
        assert conn.access_token_enc == ""
        assert conn.refresh_token_enc == ""
        assert conn.status == ContaAzulConnection.Status.DISCONNECTED


@pytest.mark.django_db
class TestCredentialsDelete:
    def test_clears_everything(self, authed_client):
        conn = ContaAzulConnection.objects.create(
            tenant=authed_client.tenant,
            client_id="x",
        )
        conn.set_client_secret("y")
        conn.set_access_token("a", expires_in=60)
        conn.save()

        resp = authed_client.delete(URL)
        assert resp.status_code == 200
        assert resp.json() == {"has_credentials": False}

        conn.refresh_from_db()
        assert conn.client_id == ""
        assert conn.client_secret_enc == ""
        assert conn.access_token_enc == ""


@pytest.mark.django_db
class TestUsingTenantCredentialsInFlow:
    """O fluxo authorize/callback deve usar as credenciais do tenant."""

    def test_authorize_uses_tenant_credentials(self, authed_client):
        conn = ContaAzulConnection.objects.create(
            tenant=authed_client.tenant,
            client_id="tenant-specific-id",
        )
        conn.set_client_secret("tenant-specific-secret")
        conn.save()

        resp = authed_client.get("/api/integrations/contaazul/authorize")
        assert resp.status_code == 200
        url = resp.json()["url"]
        assert "client_id=tenant-specific-id" in url

    def test_authorize_503_without_credentials(self, authed_client):
        # settings.CONTA_AZUL.CLIENT_ID está vazio (fixture autouse)
        # e o tenant ainda não cadastrou as suas
        resp = authed_client.get("/api/integrations/contaazul/authorize")
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "oauth_misconfigured"

    @patch("apps.integrations.views.ContaAzulOAuthService.exchange_code")
    def test_callback_uses_tenant_credentials(
        self, mock_exchange, api_client, make_tenant
    ):
        from apps.integrations.models import OAuthState

        mock_exchange.return_value = OAuthTokens(
            access_token="A", refresh_token="R", expires_in=3600, scope="openid",
        )
        t = make_tenant()
        conn = ContaAzulConnection.objects.create(
            tenant=t, client_id="tenant-id",
        )
        conn.set_client_secret("tenant-sec")
        conn.save()
        OAuthState.objects.create(state="s1", tenant=t)

        resp = api_client.get(
            "/api/integrations/contaazul/callback?code=c&state=s1"
        )
        assert resp.status_code == 302
        assert "status=connected" in resp["Location"]
