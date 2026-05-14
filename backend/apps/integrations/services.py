"""
Serviços de integração com a Conta Azul.

`ContaAzulOAuthService` encapsula:
- montagem da URL de autorização
- troca code → tokens
- refresh do access token

Não toca em models. Recebe credenciais via settings. HTTP via httpx.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx
from django.conf import settings


class OAuthError(Exception):
    """Falha no fluxo OAuth com a Conta Azul."""


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str
    expires_in: int
    scope: str
    token_type: str = "Bearer"  # noqa: S105


class ContaAzulOAuthService:
    """
    Wrapper estateless do OAuth2 Authorization Code da Conta Azul.

    Precedência das credenciais (client_id, client_secret):
    1. Argumentos explícitos do construtor (modo BYO por tenant)
    2. settings.CONTA_AZUL (fallback global, opcional)
    """

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        cfg = settings.CONTA_AZUL
        self.client_id: str = client_id if client_id is not None else cfg["CLIENT_ID"]
        self.client_secret: str = (
            client_secret if client_secret is not None else cfg["CLIENT_SECRET"]
        )
        self.redirect_uri: str = cfg["REDIRECT_URI"]
        self.auth_url: str = cfg["AUTH_URL"]
        self.token_url: str = cfg["TOKEN_URL"]
        self.scope: str = cfg["SCOPE"]
        self._http = http_client  # injetado em testes

    @classmethod
    def for_connection(cls, conn, **kwargs) -> ContaAzulOAuthService:  # type: ignore[no-untyped-def]
        """Constrói o serviço com credenciais do `ContaAzulConnection` se houver."""
        if conn.has_credentials:
            return cls(
                client_id=conn.client_id,
                client_secret=conn.client_secret,
                **kwargs,
            )
        return cls(**kwargs)

    # ------------------------------------------------------------------
    def build_authorize_url(self, *, state: str) -> str:
        """Monta a URL para redirecionar o usuário ao consent screen."""
        if not self.client_id:
            raise OAuthError(
                "Credenciais Conta Azul não configuradas. "
                "Cadastre seu app em portaldevs.contaazul.com e informe Client ID e Secret."
            )
        from urllib.parse import urlencode

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
        }
        return f"{self.auth_url}?{urlencode(params)}"

    # ------------------------------------------------------------------
    def exchange_code(self, code: str) -> OAuthTokens:
        """Troca o `code` recebido no callback por tokens."""
        return self._token_request({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        })

    def refresh(self, refresh_token: str) -> OAuthTokens:
        """Renova o access token usando o refresh token."""
        if not refresh_token:
            raise OAuthError("refresh_token vazio")
        return self._token_request({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })

    # ------------------------------------------------------------------
    def _token_request(self, data: dict[str, str]) -> OAuthTokens:
        auth_header = self._basic_auth_header()
        try:
            client = self._http or httpx.Client(timeout=15.0)
            close_client = self._http is None
            try:
                resp = client.post(
                    self.token_url,
                    data=data,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
            finally:
                if close_client:
                    client.close()
        except httpx.HTTPError as e:
            raise OAuthError(f"Falha de rede ao falar com Conta Azul: {e}") from e

        if resp.status_code >= 400:
            raise OAuthError(
                f"Conta Azul retornou {resp.status_code}: {resp.text[:300]}"
            )

        try:
            body: dict[str, Any] = resp.json()
        except ValueError as e:
            raise OAuthError("Resposta da Conta Azul não é JSON válido") from e

        try:
            return OAuthTokens(
                access_token=body["access_token"],
                refresh_token=body.get("refresh_token", ""),
                expires_in=int(body.get("expires_in", 0)),
                scope=body.get("scope", self.scope),
                token_type=body.get("token_type", "Bearer"),
            )
        except (KeyError, TypeError, ValueError) as e:
            raise OAuthError(f"Payload inesperado da Conta Azul: {e}") from e

    def _basic_auth_header(self) -> str:
        creds = f"{self.client_id}:{self.client_secret}".encode()
        return f"Basic {base64.b64encode(creds).decode('ascii')}"
