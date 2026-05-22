"""
Cliente HTTP da Conta Azul v2.

Responsabilidades:
- Anexar `Authorization: Bearer <access_token>`
- Auto-refresh quando 401
- Retry exponencial em 429 / 5xx, respeitando `Retry-After`
- Paginação (gera as páginas)

Não faz parsing/normalização — só puxa JSON e devolve.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

import httpx
from django.conf import settings
from django.utils import timezone

from apps.integrations.models import ContaAzulConnection
from apps.integrations.services import ContaAzulOAuthService, OAuthError

logger = logging.getLogger(__name__)


class ContaAzulAPIError(Exception):
    """Erro chamando a API Conta Azul (após retries)."""


class ContaAzulClient:
    """Wrapper HTTP em torno da `ContaAzulConnection`."""

    def __init__(
        self,
        connection: ContaAzulConnection,
        *,
        http_client: httpx.Client | None = None,
        max_retries: int = 4,
        page_size: int = 100,
    ) -> None:
        self.connection = connection
        self.api_base = settings.CONTA_AZUL["API_BASE"].rstrip("/")
        self._http = http_client
        self._owns_client = http_client is None
        self.max_retries = max_retries
        self.page_size = page_size

    # ------------------------------------------------------------------
    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=30.0)
        return self._http

    def close(self) -> None:
        if self._owns_client and self._http is not None:
            self._http.close()
            self._http = None

    def __enter__(self) -> ContaAzulClient:
        return self

    def __exit__(self, *exc) -> None:  # type: ignore[no-untyped-def]
        self.close()

    # ------------------------------------------------------------------
    def _ensure_access_token(self) -> str:
        """Refresca o token se estiver expirado."""
        if self.connection.is_expired() and self.connection.refresh_token_enc:
            try:
                svc = ContaAzulOAuthService.for_connection(self.connection)
                tokens = svc.refresh(self.connection.refresh_token)
            except OAuthError as e:
                self.connection.mark_error(f"refresh falhou: {e}")
                self.connection.save(update_fields=["status", "last_error", "updated_at"])
                raise ContaAzulAPIError(f"Token refresh failed: {e}") from e
            self.connection.set_access_token(tokens.access_token, expires_in=tokens.expires_in)
            if tokens.refresh_token:
                self.connection.set_refresh_token(tokens.refresh_token)
            self.connection.mark_connected()
            self.connection.save()
        return self.connection.access_token

    # ------------------------------------------------------------------
    def get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        """GET com retry. `path` é absoluto a partir do API_BASE (ex.: `/pessoas`)."""
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        attempt = 0
        last_error: Exception | None = None

        while attempt < self.max_retries:
            attempt += 1
            access = self._ensure_access_token()
            try:
                resp = self.http.get(
                    url,
                    params=params,
                    headers={
                        "Authorization": f"Bearer {access}",
                        "Accept": "application/json",
                    },
                )
            except httpx.HTTPError as e:
                last_error = e
                self._sleep_backoff(attempt)
                continue

            # 401 → tenta refresh uma vez
            if resp.status_code == 401 and attempt == 1:
                logger.info("401 do Conta Azul; forçando refresh")
                # invalida expiração para o próximo loop refrescar
                self.connection.expires_at = timezone.now()
                continue

            # 429 → respeita Retry-After
            if resp.status_code == 429:
                wait = self._retry_after_seconds(resp) or self._exp_backoff(attempt)
                logger.warning("429 Conta Azul, dormindo %.1fs", wait)
                time.sleep(wait)
                continue

            # 5xx → retry com backoff
            if 500 <= resp.status_code < 600:
                last_error = ContaAzulAPIError(
                    f"{resp.status_code} {resp.text[:200]}"
                )
                self._sleep_backoff(attempt)
                continue

            if resp.status_code >= 400:
                raise ContaAzulAPIError(
                    f"{resp.status_code} {resp.text[:300]}"
                )

            try:
                return resp.json()
            except ValueError as e:
                raise ContaAzulAPIError(f"resposta não-JSON: {e}") from e

        raise ContaAzulAPIError(
            f"Falha após {self.max_retries} tentativas: {last_error}"
        )

    # ------------------------------------------------------------------
    # Chaves possíveis para a lista de itens, em ordem de preferência
    _ITEMS_KEYS: tuple[str, ...] = ("itens", "data", "items", "content")

    def paginate(
        self,
        path: str,
        params: dict | None = None,
        *,
        items_key: str | None = None,
        page_param: str = "pagina",
        size_param: str = "tamanho_pagina",
    ) -> Iterator[dict[str, Any]]:
        """
        Gera todos os itens de um endpoint paginado da Conta Azul v2.

        Heurísticas:
        - lista pode vir em `itens` (v2 atual), `data`, `items` ou `content`
        - paginação: tenta `pagina`/`tamanho_pagina` (v2 PT-BR), aceita também `page`/`size`
        - itens_totais determina parada quando disponível
        """
        page = 1
        params = dict(params or {})
        while True:
            params[page_param] = page
            params[size_param] = self.page_size
            data = self.get(path, params=params)
            items = self._extract_items(data, preferred_key=items_key)
            if not items:
                return
            yield from items
            # Heurísticas de parada
            total = (
                data.get("itens_totais")
                or data.get("totalPages")
                or data.get("total_pages")
                or (data.get("pagination") or {}).get("totalPages")
                if isinstance(data, dict)
                else None
            )
            if total and isinstance(total, int) and page * self.page_size >= int(total):
                return
            if len(items) < self.page_size:
                return
            page += 1

    @classmethod
    def _extract_items(cls, data: Any, preferred_key: str | None = None) -> list[dict]:
        if not isinstance(data, dict):
            return []
        keys = (preferred_key, *cls._ITEMS_KEYS) if preferred_key else cls._ITEMS_KEYS
        for k in keys:
            if k and isinstance(data.get(k), list):
                return data[k]
        return []

    # ------------------------------------------------------------------
    @staticmethod
    def _retry_after_seconds(resp: httpx.Response) -> float | None:
        ra = resp.headers.get("Retry-After")
        if not ra:
            return None
        try:
            return float(ra)
        except ValueError:
            return None

    @staticmethod
    def _exp_backoff(attempt: int) -> float:
        # 1s, 2s, 4s, 8s …
        return min(2 ** (attempt - 1), 30.0)

    def _sleep_backoff(self, attempt: int) -> None:
        time.sleep(self._exp_backoff(attempt))
