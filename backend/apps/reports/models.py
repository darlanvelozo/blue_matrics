"""
SharedReport — link público read-only para um dashboard, com token opaco.

Usado para: "manda esse link pro contador / sócio / banco".
Expira em X dias (default 7); pode ser revogado.
Snapshot opcional do preset/range (pra link não mudar dado quando filtro padrão mudar).
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.tenants.models import TenantScopedModel


class SharedReport(TenantScopedModel):
    class Dashboard(models.TextChoices):
        EXECUTIVE = "executive", "Executivo"
        FINANCIAL = "financial", "Financeiro"
        COMMERCIAL = "commercial", "Comercial"

    token = models.CharField(max_length=64, unique=True, db_index=True)
    dashboard = models.CharField(max_length=20, choices=Dashboard.choices)
    # Snapshot dos parâmetros — usado pra renderizar sem login
    preset = models.CharField(max_length=20, blank=True, default="last_12m")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    view_count = models.IntegerField(default=0)

    created_by_email = models.EmailField(blank=True, default="")  # snapshot
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Shared({self.dashboard}, expires={self.expires_at:%Y-%m-%d})"

    def is_active(self) -> bool:
        if self.revoked_at:
            return False
        return timezone.now() < self.expires_at

    @classmethod
    def create_share(cls, *, tenant, dashboard: str, preset: str = "last_12m",
                     days_valid: int = 7, created_by_email: str = ""):  # type: ignore[no-untyped-def]
        return cls.objects.create(
            tenant=tenant,
            dashboard=dashboard,
            preset=preset,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(days=days_valid),
            created_by_email=created_by_email[:254],
        )
