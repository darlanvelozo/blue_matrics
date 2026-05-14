"""Modelos de tenancy."""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

from .context import current_tenant_id
from .managers import TenantScopedManager, UnscopedManager


class Tenant(models.Model):
    """Uma empresa cliente do SaaS."""

    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        SUSPENDED = "suspended", "Suspended"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=18, blank=True, default="", db_index=True)
    slug = models.SlugField(max_length=64, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.TRIAL)
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"

    def is_trial_active(self) -> bool:
        if self.status != self.Status.TRIAL or self.trial_ends_at is None:
            return False
        return timezone.now() < self.trial_ends_at


class TenantScopedModel(models.Model):
    """
    Base abstrata para qualquer modelo cujos dados pertencem a um tenant.
    Usa `objects` (filtrado) e `unsafe_objects` (sem filtro — APENAS para
    código admin/migrations/scripts).
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="+",
        editable=False,
        db_index=True,
    )

    objects = TenantScopedManager()
    unsafe_objects = UnscopedManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Preenche tenant a partir do contexto se ainda não tiver
        if not self.tenant_id:
            tid = current_tenant_id()
            if tid is None:
                raise ValueError(
                    f"{self.__class__.__name__}.save() sem tenant no contexto. "
                    f"Use set_current_tenant(...) ou atribua tenant_id explicitamente."
                )
            self.tenant_id = tid
        super().save(*args, **kwargs)
