"""
Adapters de billing — Stripe real e mock.

- `StripeBillingService` (real): usa stripe SDK quando STRIPE_SECRET_KEY está setada.
- `MockBillingService` (dev): simula checkout e cobrança, "completa" assinaturas
  imediatamente. Permite desenvolver e testar todo o fluxo sem precisar de Stripe.

`get_billing_service()` escolhe automaticamente baseado no settings.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone

from .models import Invoice, Plan, Subscription

logger = logging.getLogger(__name__)


class BillingError(Exception):
    """Falha em operação de billing."""


@dataclass(frozen=True)
class CheckoutSession:
    url: str
    session_id: str


class BillingService(Protocol):
    name: str

    def create_checkout_session(
        self,
        *,
        subscription: Subscription,
        plan: Plan,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession: ...

    def cancel_subscription(self, subscription: Subscription) -> None: ...

    def reactivate_subscription(self, subscription: Subscription) -> None: ...


# ---------------------------------------------------------------------------
# Mock — usado em dev/teste sem Stripe configurado
# ---------------------------------------------------------------------------
class MockBillingService:
    """
    Implementação de dev: cria a subscription ATIVA e a primeira fatura PAGA
    no momento do checkout, sem passar por gateway.
    """

    name = "mock"

    def create_checkout_session(
        self,
        *,
        subscription: Subscription,
        plan: Plan,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        # Em dev: "ativa" imediatamente. Em vez de redirecionar pro Stripe,
        # devolvemos uma URL local que marca como sucesso quando aberta.
        session_id = f"mock_cs_{uuid.uuid4().hex[:12]}"
        # Já efetiva a assinatura
        self._complete(subscription, plan, session_id)
        # Frontend usa este flag (?mock_checkout=ok) pra mostrar banner de sucesso
        url = f"{success_url}?status=success&mock=1&session_id={session_id}"
        return CheckoutSession(url=url, session_id=session_id)

    def cancel_subscription(self, subscription: Subscription) -> None:
        subscription.cancel_at_period_end = True
        subscription.save(update_fields=["cancel_at_period_end", "updated_at"])

    def reactivate_subscription(self, subscription: Subscription) -> None:
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.save(
            update_fields=["cancel_at_period_end", "canceled_at", "updated_at"]
        )

    # ------------------------------------------------------------------
    def _complete(self, subscription: Subscription, plan: Plan, session_id: str) -> None:
        now = timezone.now()
        period_delta = (
            relativedelta(years=1)
            if plan.billing_interval == Plan.BillingInterval.YEAR
            else relativedelta(months=1)
        )
        period_end = now + period_delta
        subscription.plan = plan
        subscription.status = Subscription.Status.ACTIVE
        subscription.current_period_start = now
        subscription.current_period_end = period_end
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.stripe_customer_id = f"mock_cus_{subscription.tenant_id}"
        subscription.stripe_subscription_id = f"mock_sub_{subscription.tenant_id}"
        subscription.save()

        Invoice.objects.create(
            tenant=subscription.tenant,
            subscription=subscription,
            amount=plan.billing_amount or plan.price_monthly,
            currency=plan.currency,
            status=Invoice.Status.PAID,
            period_start=now.date(),
            period_end=period_end.date(),
            paid_at=now,
            hosted_invoice_url=f"#mock-invoice-{session_id}",
            stripe_invoice_id=f"mock_in_{uuid.uuid4().hex[:12]}",
        )


# ---------------------------------------------------------------------------
# Real — chama Stripe SDK
# ---------------------------------------------------------------------------
class StripeBillingService:
    name = "stripe"

    def __init__(self, api_key: str) -> None:
        try:
            import stripe  # type: ignore[import-untyped]
        except ImportError as e:  # pragma: no cover
            raise BillingError(
                "stripe SDK não instalado. Adicione 'stripe' a pyproject."
            ) from e
        stripe.api_key = api_key
        self._stripe = stripe

    def _get_or_create_customer(self, subscription: Subscription) -> str:
        if subscription.stripe_customer_id:
            return subscription.stripe_customer_id
        customer = self._stripe.Customer.create(
            metadata={"tenant_id": str(subscription.tenant_id)},
            name=subscription.tenant.name,
        )
        subscription.stripe_customer_id = customer.id
        subscription.save(update_fields=["stripe_customer_id", "updated_at"])
        return customer.id

    def create_checkout_session(
        self,
        *,
        subscription: Subscription,
        plan: Plan,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        if not plan.stripe_price_id:
            raise BillingError(
                f"Plano {plan.code} sem stripe_price_id. "
                "Cadastre o preço no Stripe e atualize o catálogo."
            )
        customer_id = self._get_or_create_customer(subscription)
        session = self._stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=success_url + "?status=success&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url + "?status=canceled",
            metadata={
                "tenant_id": str(subscription.tenant_id),
                "plan_code": plan.code,
            },
        )
        return CheckoutSession(url=session.url, session_id=session.id)

    def cancel_subscription(self, subscription: Subscription) -> None:
        if not subscription.stripe_subscription_id:
            return
        self._stripe.Subscription.modify(
            subscription.stripe_subscription_id, cancel_at_period_end=True
        )
        subscription.cancel_at_period_end = True
        subscription.save(update_fields=["cancel_at_period_end", "updated_at"])

    def reactivate_subscription(self, subscription: Subscription) -> None:
        if not subscription.stripe_subscription_id:
            return
        self._stripe.Subscription.modify(
            subscription.stripe_subscription_id, cancel_at_period_end=False
        )
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.save(
            update_fields=["cancel_at_period_end", "canceled_at", "updated_at"]
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_billing_service() -> BillingService:
    """
    Retorna o adapter ativo. Se STRIPE_SECRET_KEY estiver setada, usa Stripe;
    senão, mock (dev/teste).
    """
    key = (getattr(settings, "STRIPE_SECRET_KEY", "") or "").strip()
    if key and not key.startswith("change-me"):
        try:
            return StripeBillingService(api_key=key)
        except BillingError as e:
            logger.warning("Stripe indisponível, caindo no mock: %s", e)
    return MockBillingService()


# ---------------------------------------------------------------------------
# Helpers de domínio (trial, criar sub default)
# ---------------------------------------------------------------------------
def ensure_subscription_for_tenant(tenant, *, default_plan_code: str = "monthly") -> Subscription:
    """
    Cria uma Subscription em trial 7d para o tenant se ainda não tiver.
    Idempotente. Usado no momento do signup.
    """
    sub = Subscription.objects.filter(tenant=tenant).first()
    if sub:
        return sub
    plan = Plan.objects.filter(code=default_plan_code, is_active=True).first()
    if plan is None:
        plan = Plan.objects.filter(is_active=True).order_by("price_monthly").first()
    if plan is None:
        raise BillingError("Nenhum Plan ativo cadastrado. Rode as migrations.")
    return Subscription.objects.create(
        tenant=tenant,
        plan=plan,
        status=Subscription.Status.TRIALING,
        trial_ends_at=timezone.now() + timedelta(days=7),
    )
