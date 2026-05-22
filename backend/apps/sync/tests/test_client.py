"""Testes do ContaAzulClient com httpx.MockTransport."""
from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
from django.utils import timezone

from apps.integrations.models import ContaAzulConnection
from apps.integrations.services import OAuthTokens
from apps.sync.client import ContaAzulAPIError, ContaAzulClient


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.CONTA_AZUL = {
        "CLIENT_ID": "cid",
        "CLIENT_SECRET": "csec",
        "REDIRECT_URI": "http://x",
        "AUTH_URL": "https://auth.contaazul.com/oauth2/authorize",
        "TOKEN_URL": "https://auth.contaazul.com/oauth2/token",
        "API_BASE": "https://api-v2.contaazul.com/v1",
        "SCOPE": "openid",
    }


@pytest.fixture
def connection(make_tenant):
    t = make_tenant()
    conn = ContaAzulConnection.objects.create(tenant=t, client_id="cid")
    conn.set_client_secret("csec")
    conn.set_access_token("valid-token", expires_in=3600)
    conn.set_refresh_token("refresh-x")
    conn.mark_connected()
    conn.save()
    return conn


@pytest.mark.django_db
class TestGet:
    def test_basic_get(self, connection):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["url"] = str(req.url)
            captured["auth"] = req.headers.get("Authorization", "")
            return httpx.Response(200, json={"ok": True, "data": [1, 2]})

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client = ContaAzulClient(connection, http_client=http)
            data = client.get("/pessoas", params={"page": 1})

        assert data == {"ok": True, "data": [1, 2]}
        assert "pessoas" in captured["url"]
        assert captured["auth"] == "Bearer valid-token"

    def test_429_respects_retry_after(self, connection):
        calls = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200, json={"data": []})

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client = ContaAzulClient(connection, http_client=http, max_retries=3)
            data = client.get("/x")

        assert data == {"data": []}
        assert calls["n"] == 2

    def test_5xx_retries(self, connection):
        calls = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] < 2:
                return httpx.Response(500, text="boom")
            return httpx.Response(200, json={"ok": True})

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client = ContaAzulClient(connection, http_client=http, max_retries=3)
            data = client.get("/x")

        assert data == {"ok": True}
        assert calls["n"] == 2

    def test_4xx_non_429_raises_immediately(self, connection):
        def handler(_r: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="forbidden")

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client = ContaAzulClient(connection, http_client=http)
            with pytest.raises(ContaAzulAPIError, match="403"):
                client.get("/x")

    def test_max_retries_exhausted(self, connection):
        def handler(_r: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client = ContaAzulClient(connection, http_client=http, max_retries=2)
            with pytest.raises(ContaAzulAPIError):
                client.get("/x")

    def test_401_triggers_refresh(self, connection, monkeypatch):
        """Após 401, force expirar e o cliente refresca via OAuthService."""
        # Simula token expirado para entrar no fluxo de refresh
        connection.expires_at = timezone.now() - timedelta(seconds=10)
        connection.save()

        # Mock do refresh
        from apps.integrations import services as svc_mod

        def fake_refresh(self, refresh_token):
            return OAuthTokens(
                access_token="new-token",
                refresh_token="new-refresh",
                expires_in=3600,
                scope="openid",
            )

        monkeypatch.setattr(svc_mod.ContaAzulOAuthService, "refresh", fake_refresh)

        seen_tokens: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            seen_tokens.append(req.headers.get("Authorization", ""))
            return httpx.Response(200, json={"data": []})

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client = ContaAzulClient(connection, http_client=http)
            client.get("/x")

        # primeira chamada já vai com token novo (refresh aconteceu antes do GET)
        assert seen_tokens[0] == "Bearer new-token"


@pytest.mark.django_db
class TestPaginate:
    def test_paginates_until_empty(self, connection):
        pages = {
            1: [{"id": "a"}, {"id": "b"}],
            2: [{"id": "c"}],
            3: [],
        }

        def handler(req: httpx.Request) -> httpx.Response:
            page = int(httpx.QueryParams(req.url.query).get("pagina", 1))
            return httpx.Response(200, json={"itens": pages[page]})

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client = ContaAzulClient(connection, http_client=http, page_size=2)
            items = list(client.paginate("/x"))

        assert [i["id"] for i in items] == ["a", "b", "c"]
