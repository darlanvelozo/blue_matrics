"""Testes do ContaAzulOAuthService (com httpx MockTransport)."""
from __future__ import annotations

import base64
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from apps.integrations.services import ContaAzulOAuthService, OAuthError

VALID_CFG = {
    "CLIENT_ID": "test-client",
    "CLIENT_SECRET": "test-secret",
    "REDIRECT_URI": "http://localhost:8000/api/integrations/contaazul/callback",
    "AUTH_URL": "https://auth.contaazul.com/oauth2/authorize",
    "TOKEN_URL": "https://auth.contaazul.com/oauth2/token",
    "API_BASE": "https://api-v2.contaazul.com/v1",
    "SCOPE": "openid profile aws.cognito.signin.user.admin",
}


@pytest.fixture
def configured_settings(settings):
    settings.CONTA_AZUL = VALID_CFG
    return settings


class TestService:
    def test_authorize_url_contains_all_params(self, configured_settings):
        svc = ContaAzulOAuthService()
        url = svc.build_authorize_url(state="abc123")
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        assert parsed.netloc == "auth.contaazul.com"
        assert parsed.path == "/oauth2/authorize"
        assert qs["response_type"] == ["code"]
        assert qs["client_id"] == ["test-client"]
        assert qs["state"] == ["abc123"]
        assert qs["redirect_uri"] == [
            "http://localhost:8000/api/integrations/contaazul/callback"
        ]
        assert "openid" in qs["scope"][0]

    def test_authorize_url_raises_without_client_id(self, settings):
        settings.CONTA_AZUL = {**VALID_CFG, "CLIENT_ID": ""}
        svc = ContaAzulOAuthService()
        with pytest.raises(OAuthError, match="Credenciais"):
            svc.build_authorize_url(state="x")

    # ------------------------------------------------------------------
    def test_exchange_code_success(self, configured_settings):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("Authorization", "")
            captured["body"] = dict(httpx.QueryParams(request.content.decode()))
            captured["url"] = str(request.url)
            return httpx.Response(
                200,
                json={
                    "access_token": "acc-1",
                    "refresh_token": "ref-1",
                    "expires_in": 3600,
                    "scope": "openid",
                    "token_type": "Bearer",
                },
            )

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as http:
            svc = ContaAzulOAuthService(http_client=http)
            tokens = svc.exchange_code("the-code")

        assert tokens.access_token == "acc-1"
        assert tokens.refresh_token == "ref-1"
        assert tokens.expires_in == 3600
        assert captured["url"].startswith("https://auth.contaazul.com/oauth2/token")
        assert captured["body"]["grant_type"] == "authorization_code"
        assert captured["body"]["code"] == "the-code"

        expected = "Basic " + base64.b64encode(b"test-client:test-secret").decode("ascii")
        assert captured["auth"] == expected

    def test_exchange_code_http_error_raises(self, configured_settings):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "invalid_grant"})

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as http:
            svc = ContaAzulOAuthService(http_client=http)
            with pytest.raises(OAuthError, match="400"):
                svc.exchange_code("bad")

    def test_refresh_success(self, configured_settings):
        def handler(request: httpx.Request) -> httpx.Response:
            body = dict(httpx.QueryParams(request.content.decode()))
            assert body["grant_type"] == "refresh_token"
            assert body["refresh_token"] == "ref-old"
            return httpx.Response(
                200,
                json={
                    "access_token": "acc-new",
                    "refresh_token": "ref-new",
                    "expires_in": 1800,
                    "scope": "openid",
                },
            )

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as http:
            svc = ContaAzulOAuthService(http_client=http)
            tokens = svc.refresh("ref-old")

        assert tokens.access_token == "acc-new"
        assert tokens.refresh_token == "ref-new"
        assert tokens.expires_in == 1800

    def test_refresh_empty_token_raises(self, configured_settings):
        svc = ContaAzulOAuthService()
        with pytest.raises(OAuthError, match="refresh_token"):
            svc.refresh("")

    def test_exchange_code_non_json_response_raises(self, configured_settings):
        def handler(_r: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"<html>nope</html>")

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as http:
            svc = ContaAzulOAuthService(http_client=http)
            with pytest.raises(OAuthError, match="JSON"):
                svc.exchange_code("x")
