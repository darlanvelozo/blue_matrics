"""Testes dos endpoints de dashboards."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.sync.models import Sale


@pytest.mark.django_db
class TestExecutiveView:
    URL = "/api/dashboards/executive"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_returns_summary(self, authed_client):
        resp = authed_client.get(self.URL + "?preset=this_month")
        assert resp.status_code == 200
        body = resp.json()
        assert "revenue" in body
        assert "net_profit" in body
        assert "revenue_by_month" in body
        assert "has_data" in body
        assert body["has_data"] is False  # nenhum dado ainda

    def test_has_data_true_when_sales_exist(self, authed_client):
        Sale.unsafe_objects.create(
            tenant_id=authed_client.tenant.id,
            external_id="s1",
            status=Sale.Status.CLOSED,
            issued_at=timezone.make_aware(datetime(2026, 4, 5, 12)),
            total=Decimal("100"),
        )
        resp = authed_client.get(self.URL + "?preset=this_month")
        assert resp.status_code == 200
        assert resp.json()["has_data"] is True

    def test_explicit_range(self, authed_client):
        resp = authed_client.get(self.URL + "?start=2026-01-01&end=2026-03-31")
        assert resp.status_code == 200
        assert resp.json()["period"] == {"start": "2026-01-01", "end": "2026-03-31"}

    def test_yoy_comparison(self, authed_client):
        resp = authed_client.get(self.URL + "?preset=this_month&comparison=yoy")
        assert resp.status_code == 200
        assert resp.json()["comparison_mode"] == "yoy"


@pytest.mark.django_db
class TestFinancialView:
    URL = "/api/dashboards/financial"

    def test_returns_summary(self, authed_client):
        resp = authed_client.get(self.URL + "?preset=last_30d")
        assert resp.status_code == 200
        body = resp.json()
        assert "cash_in" in body
        assert "cash_out" in body
        assert "cashflow_by_month" in body


@pytest.mark.django_db
class TestCommercialView:
    URL = "/api/dashboards/commercial"

    def test_returns_summary(self, authed_client):
        resp = authed_client.get(self.URL + "?preset=last_90d")
        assert resp.status_code == 200
        body = resp.json()
        assert "revenue" in body
        assert "top_customers" in body
        assert "top_products" in body
        assert "by_salesperson" in body
