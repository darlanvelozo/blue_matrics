"""Testes dos endpoints de billing."""
from __future__ import annotations

import pytest

from apps.billing.models import Invoice, Plan, Subscription


@pytest.mark.django_db
class TestListPlans:
    URL = "/api/billing/plans"

    def test_public(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        plans = resp.json()["plans"]
        # Mensal + Semestral + Anual estão ativos; legacy ficam is_active=False
        assert len(plans) == 3
        codes = [p["code"] for p in plans]
        assert "monthly" in codes
        assert "semestral" in codes
        assert "annual" in codes


@pytest.mark.django_db
class TestSubscription:
    URL = "/api/billing/subscription"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_creates_trial_on_first_access(self, authed_client):
        # Ainda não tem Subscription
        assert not Subscription.objects.filter(tenant=authed_client.tenant).exists()
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body["subscription"]["status"] == "trialing"
        assert body["subscription"]["plan"]["code"] == "monthly"
        assert body["subscription"]["is_active"] is True
        assert body["provider"] == "mock"
        # Agora existe
        assert Subscription.objects.filter(tenant=authed_client.tenant).exists()


@pytest.mark.django_db
class TestCheckout:
    URL = "/api/billing/checkout"

    def test_requires_auth(self, api_client):
        assert api_client.post(self.URL, {"plan_code": "annual"}, format="json").status_code == 401

    def test_missing_plan(self, authed_client):
        resp = authed_client.post(self.URL, {}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "missing_plan"

    def test_invalid_plan(self, authed_client):
        resp = authed_client.post(self.URL, {"plan_code": "noexist"}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_plan"

    def test_mock_completes_subscription(self, authed_client):
        resp = authed_client.post(self.URL, {"plan_code": "annual"}, format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert "mock=1" in body["url"]
        sub = Subscription.objects.get(tenant=authed_client.tenant)
        assert sub.status == "active"
        assert sub.plan.code == "annual"
        # criou fatura paga
        assert Invoice.objects.filter(tenant=authed_client.tenant, status="paid").count() == 1


@pytest.mark.django_db
class TestCancelReactivate:
    def test_cancel(self, authed_client):
        # cria sub primeiro via subscription endpoint
        authed_client.get("/api/billing/subscription")
        resp = authed_client.post("/api/billing/cancel")
        assert resp.status_code == 200
        assert resp.json()["cancel_at_period_end"] is True

    def test_reactivate(self, authed_client):
        authed_client.get("/api/billing/subscription")
        sub = Subscription.objects.get(tenant=authed_client.tenant)
        sub.cancel_at_period_end = True
        sub.save()
        resp = authed_client.post("/api/billing/reactivate")
        assert resp.status_code == 200
        assert resp.json()["cancel_at_period_end"] is False

    def test_cancel_without_subscription(self, authed_client):
        resp = authed_client.post("/api/billing/cancel")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "no_subscription"


@pytest.mark.django_db
class TestTenantIsolation:
    def test_subscription_isolated(self, authed_client, make_tenant):
        other = make_tenant("other")
        other_plan = Plan.objects.get(code="annual")
        Subscription.objects.create(
            tenant=other, plan=other_plan, status=Subscription.Status.ACTIVE
        )
        body = authed_client.get("/api/billing/subscription").json()
        # Para o authed_client (tenant diferente), retorna trial novo, não a do other
        assert body["subscription"]["plan"]["code"] == "monthly"
        assert body["subscription"]["status"] == "trialing"


@pytest.mark.django_db
class TestWebhookView:
    URL = "/api/billing/webhook/stripe"

    def test_no_secret_returns_ok(self, api_client, settings):
        settings.STRIPE_WEBHOOK_SECRET = ""
        resp = api_client.post(self.URL, {}, format="json")
        assert resp.status_code == 200
        assert resp.json()["received"] is True
