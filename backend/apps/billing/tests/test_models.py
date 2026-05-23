"""Testes dos models de billing."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.billing.models import Plan, Subscription


@pytest.mark.django_db
class TestPlanSeed:
    def test_active_plans_are_monthly_and_annual(self):
        codes = list(Plan.objects.filter(is_active=True).values_list("code", flat=True).order_by("code"))
        assert codes == ["annual", "monthly"]

    def test_monthly_plan(self):
        p = Plan.objects.get(code="monthly")
        assert p.billing_amount == 499
        assert p.billing_interval == "month"

    def test_annual_plan(self):
        p = Plan.objects.get(code="annual")
        assert p.billing_amount == 4499
        assert p.billing_interval == "year"


@pytest.mark.django_db
class TestSubscription:
    def _make(self, tenant, **kwargs):
        plan = Plan.objects.get(code=kwargs.pop("plan_code", "monthly"))
        defaults = {
            "tenant": tenant,
            "plan": plan,
            "status": Subscription.Status.TRIALING,
            "trial_ends_at": timezone.now() + timedelta(days=7),
        }
        defaults.update(kwargs)
        return Subscription.objects.create(**defaults)

    def test_is_trialing_when_in_future(self, make_tenant):
        sub = self._make(make_tenant())
        assert sub.is_trialing is True
        assert sub.trial_expired is False
        assert sub.is_active is True

    def test_trial_expired_when_past(self, make_tenant):
        sub = self._make(make_tenant(), trial_ends_at=timezone.now() - timedelta(days=1))
        assert sub.is_trialing is False
        assert sub.trial_expired is True

    def test_active_is_active(self, make_tenant):
        sub = self._make(make_tenant(), status=Subscription.Status.ACTIVE)
        assert sub.is_active is True
        assert sub.is_trialing is False

    def test_canceled_not_active(self, make_tenant):
        sub = self._make(make_tenant(), status=Subscription.Status.CANCELED)
        assert sub.is_active is False
