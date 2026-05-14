"""
Conexão OAuth2 entre um tenant e a Conta Azul.

Tokens são guardados criptografados (Fernet). Use os helpers
`set_access_token` / `set_refresh_token` em vez de gravar nos campos brutos.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.tenants.models import Tenant

from .crypto import decrypt, encrypt


class ContaAzulConnection(models.Model):
    class Status(models.TextChoices):
        DISCONNECTED = "disconnected", "Desconectado"
        CONNECTED = "connected", "Conectado"
        ERROR = "error", "Erro"
        REVOKED = "revoked", "Revogado"

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="contaazul_connection",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DISCONNECTED,
    )

    # credenciais do app OAuth (BYO — o usuário cadastra no portaldevs.contaazul.com)
    client_id = models.CharField(max_length=255, blank=True, default="")
    client_secret_enc = models.TextField(blank=True, default="")

    # tokens criptografados
    access_token_enc = models.TextField(blank=True, default="")
    refresh_token_enc = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    scope = models.CharField(max_length=255, blank=True, default="")

    # contexto da última operação
    last_error = models.TextField(blank=True, default="")
    last_synced_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)

    # auditoria
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"ContaAzul({self.tenant.slug}, {self.status})"

    # ------------------------------------------------------------------
    # credenciais (helpers)
    # ------------------------------------------------------------------
    def set_client_secret(self, secret: str) -> None:
        self.client_secret_enc = encrypt(secret) if secret else ""

    @property
    def client_secret(self) -> str:
        return decrypt(self.client_secret_enc) if self.client_secret_enc else ""

    @property
    def has_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret_enc)

    # ------------------------------------------------------------------
    # tokens (helpers)
    # ------------------------------------------------------------------
    def set_access_token(self, token: str, expires_in: int | None = None) -> None:
        self.access_token_enc = encrypt(token)
        if expires_in is not None:
            self.expires_at = timezone.now() + timedelta(seconds=int(expires_in))

    def set_refresh_token(self, token: str) -> None:
        self.refresh_token_enc = encrypt(token)

    @property
    def access_token(self) -> str:
        return decrypt(self.access_token_enc) if self.access_token_enc else ""

    @property
    def refresh_token(self) -> str:
        return decrypt(self.refresh_token_enc) if self.refresh_token_enc else ""

    # ------------------------------------------------------------------
    # estado
    # ------------------------------------------------------------------
    def is_expired(self, *, skew_seconds: int = 30) -> bool:
        if not self.expires_at:
            return True
        return timezone.now() >= (self.expires_at - timedelta(seconds=skew_seconds))

    def mark_connected(self) -> None:
        self.status = self.Status.CONNECTED
        self.last_error = ""
        if not self.connected_at:
            self.connected_at = timezone.now()

    def mark_error(self, message: str) -> None:
        self.status = self.Status.ERROR
        self.last_error = (message or "")[:1000]


class OAuthState(models.Model):
    """
    Estado anti-CSRF do fluxo OAuth (parâmetro `state`).
    Guarda quem iniciou o fluxo e referência ao tenant para amarrar o callback.

    TTL curto (10min). Quando o callback chega, validamos:
    - state existe
    - não expirou
    - ainda não foi consumido
    """

    state = models.CharField(max_length=64, unique=True, db_index=True)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="contaazul_oauth_states"
    )
    initiated_by_email = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["created_at"])]

    def __str__(self) -> str:
        return f"OAuthState({self.state[:8]}…, tenant={self.tenant_id})"

    def is_expired(self) -> bool:
        return timezone.now() >= self.created_at + timedelta(minutes=10)

    def is_consumed(self) -> bool:
        return self.consumed_at is not None
