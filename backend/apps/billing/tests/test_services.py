"""Testes do BillingService (mock)."""
from __future__ import annotations

import pytest

from apps.billing.models import Invoice, Plan, Subscription
from apps.billing.services import (
    MockBillingService,
    StripeBillingService,
    ensure_subscription_for_tenant,
    get_billing_service,
)


@pytest.mark.django_db
class TestMockBillingService:
    def test_create_checkout_completes_subscription(self, make_tenant):
        t = make_tenant()
        sub = ensure_subscription_for_tenant(t)
        plan = Plan.objects.get(code="growth")

        svc = MockBillingService()
        session = svc.create_checkout_session(
            subscription=sub, plan=plan,
            success_url="http://localhost:3000/app/billing",
            cancel_url="http://localhost:3000/app/billing",
        )
        assert "mock=1" in session.url
        assert "session_id=" in session.url

        sub.refresh_from_db()
        assert sub.status == Subscription.Status.ACTIVE
        assert sub.plan == plan
        assert sub.current_period_end is not None
        # Fatura criada
        assert Invoice.objects.filter(tenant=t, status=Invoice.Status.PAID).count() == 1
        assert Invoice.objects.filter(tenant=t).first().amount == plan.price_monthly

    def test_cancel_sets_cancel_at_period_end(self, make_tenant):
        t = make_tenant()
        sub = ensure_subscription_for_tenant(t)
        MockBillingService().cancel_subscription(sub)
        sub.refresh_from_db()
        assert sub.cancel_at_period_end is True

    def test_reactivate_clears_cancel(self, make_tenant):
        t = make_tenant()
        sub = ensure_subscription_for_tenant(t)
        sub.cancel_at_period_end = True
        sub.save()
        MockBillingService().reactivate_subscription(sub)
        sub.refresh_from_db()
        assert sub.cancel_at_period_end is False


@pytest.mark.django_db
class TestEnsureSubscription:
    def test_creates_trial_subscription(self, make_tenant):
        t = make_tenant()
        sub = ensure_subscription_for_tenant(t)
        assert sub.status == Subscription.Status.TRIALING
        assert sub.plan.code == "starter"
        assert sub.trial_ends_at is not None

    def test_idempotent(self, make_tenant):
        t = make_tenant()
        s1 = ensure_subscription_for_tenant(t)
        s2 = ensure_subscription_for_tenant(t)
        assert s1.id == s2.id


@pytest.mark.django_db
class TestFactory:
    def test_returns_mock_when_no_key(self, settings):
        settings.STRIPE_SECRET_KEY = ""
        assert get_billing_service().name == "mock"

    def test_returns_mock_when_placeholder(self, settings):
        settings.STRIPE_SECRET_KEY = "change-me-fake"
        assert get_billing_service().name == "mock"

    def test_returns_stripe_when_key_set(self, settings):
        # Stripe SDK é opcional — pula se não instalado (factory cai no mock)
        pytest.importorskip("stripe")
        settings.STRIPE_SECRET_KEY = "sk_test_realsih_123"
        svc = get_billing_service()
        assert isinstance(svc, StripeBillingService)
        assert svc.name == "stripe"
