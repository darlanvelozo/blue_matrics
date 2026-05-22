"""
Billing — planos, assinaturas e faturas.

Convenções:
- `Plan` é seedado por migration; não tem `tenant` (catálogo público)
- `Subscription` é 1:1 com Tenant (ativa por tenant)
- `Invoice` é histórico de cobranças

Stripe IDs ficam guardados quando integração real está ativa; em mock são None.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.tenants.models import Tenant


class Plan(models.Model):
    class Code(models.TextChoices):
        STARTER = "starter", "Starter"
        GROWTH = "growth", "Growth"
        BUSINESS = "business", "Business"

    code = models.CharField(max_length=32, choices=Code.choices, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200, blank=True, default="")
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    currency = models.CharField(max_length=3, default="BRL")
    max_users = models.IntegerField(default=1)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    stripe_price_id = models.CharField(max_length=80, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "price_monthly"]

    def __str__(self) -> str:
        return f"{self.name} (R$ {self.price_monthly})"


class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Em trial"
        ACTIVE = "active", "Ativa"
        PAST_DUE = "past_due", "Vencida"
        CANCELED = "canceled", "Cancelada"
        INCOMPLETE = "incomplete", "Pagamento incompleto"

    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.TRIALING)

    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)

    # Stripe (vazios em modo mock)
    stripe_customer_id = models.CharField(max_length=80, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=80, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["current_period_end"]),
        ]

    def __str__(self) -> str:
        return f"Sub({self.tenant.slug}, {self.plan.code}, {self.status})"

    @property
    def is_active(self) -> bool:
        return self.status in (self.Status.TRIALING, self.Status.ACTIVE)

    @property
    def is_trialing(self) -> bool:
        if self.status != self.Status.TRIALING:
            return False
        return bool(self.trial_ends_at and self.trial_ends_at > timezone.now())

    @property
    def trial_expired(self) -> bool:
        if self.status != self.Status.TRIALING:
            return False
        return bool(self.trial_ends_at and self.trial_ends_at <= timezone.now())


class Invoice(models.Model):
    """Fatura individual (uma por ciclo de cobrança)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        OPEN = "open", "Em aberto"
        PAID = "paid", "Paga"
        VOID = "void", "Anulada"
        UNCOLLECTIBLE = "uncollectible", "Não cobrável"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="invoices",
        null=True, blank=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    currency = models.CharField(max_length=3, default="BRL")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    hosted_invoice_url = models.URLField(max_length=500, blank=True, default="")
    invoice_pdf_url = models.URLField(max_length=500, blank=True, default="")
    stripe_invoice_id = models.CharField(max_length=80, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"Invoice({self.tenant.slug}, R$ {self.amount}, {self.status})"
