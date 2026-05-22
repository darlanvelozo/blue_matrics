"""Testes dos endpoints de reports (export + shares + public)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.reports.models import SharedReport
from apps.sync.models import Customer, Sale


def _dt(y, m, d, h=12):
    return timezone.make_aware(datetime(y, m, d, h))


@pytest.fixture
def with_sales(authed_client):
    """Cria algumas vendas para que os exporters tenham o que mostrar."""
    c = Customer.unsafe_objects.create(
        tenant_id=authed_client.tenant.id, external_id="c", name="Cliente X",
    )
    for i in range(3):
        Sale.unsafe_objects.create(
            tenant_id=authed_client.tenant.id,
            external_id=f"s{i}",
            status=Sale.Status.CLOSED,
            customer=c,
            issued_at=_dt(2026, 4, i + 1),
            total=Decimal(str(100 * (i + 1))),
        )
    return authed_client


@pytest.mark.django_db
class TestExportView:
    def test_requires_auth(self, api_client):
        resp = api_client.get("/api/reports/export/executive/excel")
        assert resp.status_code == 401

    def test_executive_excel(self, with_sales):
        resp = with_sales.get("/api/reports/export/executive/excel")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp["Content-Type"]
        # XLSX = ZIP que começa com PK
        assert resp.content[:2] == b"PK"
        assert "attachment" in resp["Content-Disposition"]

    def test_financial_html(self, with_sales):
        resp = with_sales.get("/api/reports/export/financial/html")
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/html")
        assert b"<!doctype html>" in resp.content.lower() or b"<!DOCTYPE html>" in resp.content

    def test_invalid_dashboard(self, with_sales):
        resp = with_sales.get("/api/reports/export/bogus/excel")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_dashboard"

    def test_invalid_format(self, with_sales):
        resp = with_sales.get("/api/reports/export/executive/pdf")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_format"


@pytest.mark.django_db
class TestShares:
    URL = "/api/reports/shares"

    def test_create_share(self, authed_client):
        resp = authed_client.post(self.URL, {
            "dashboard": "executive",
            "preset": "last_12m",
            "days_valid": 7,
        }, format="json")
        assert resp.status_code == 201, resp.content
        d = resp.json()
        assert d["dashboard"] == "executive"
        assert d["url_path"].startswith("/r/")
        assert d["is_active"] is True
        assert len(d["token"]) > 20

    def test_list_returns_shares(self, authed_client):
        SharedReport.create_share(
            tenant=authed_client.tenant,
            dashboard="financial",
            preset="last_12m",
            days_valid=7,
        )
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        assert len(resp.json()["shares"]) >= 1

    def test_invalid_dashboard(self, authed_client):
        resp = authed_client.post(self.URL, {"dashboard": "x"}, format="json")
        assert resp.status_code == 400

    def test_days_valid_clamped(self, authed_client):
        resp = authed_client.post(self.URL, {
            "dashboard": "executive",
            "days_valid": 9999,
        }, format="json")
        assert resp.status_code == 201
        # se chegou aqui sem erro, a clampagem rolou (max 90 dias)

    def test_revoke(self, authed_client):
        share = SharedReport.create_share(
            tenant=authed_client.tenant,
            dashboard="commercial",
        )
        resp = authed_client.delete(f"{self.URL}/{share.id}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["is_active"] is False
        assert d["revoked_at"] is not None

    def test_isolation_by_tenant(self, authed_client, make_tenant):
        other = make_tenant("other")
        SharedReport.create_share(tenant=other, dashboard="executive")
        resp = authed_client.get(self.URL)
        # ainda lista mas só do tenant do client (vazio)
        assert resp.json()["shares"] == []


@pytest.mark.django_db
class TestPublicShare:
    def test_returns_html(self, authed_client, with_sales):
        share = SharedReport.create_share(
            tenant=authed_client.tenant,
            dashboard="executive",
        )
        # endpoint público — sem auth
        from rest_framework.test import APIClient
        public = APIClient()
        resp = public.get(f"/r/{share.token}")
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/html")
        assert b"BlueMetrics" in resp.content

    def test_increments_view_count(self, authed_client, with_sales):
        share = SharedReport.create_share(
            tenant=authed_client.tenant,
            dashboard="financial",
        )
        from rest_framework.test import APIClient
        public = APIClient()
        public.get(f"/r/{share.token}")
        public.get(f"/r/{share.token}")
        share.refresh_from_db()
        assert share.view_count == 2

    def test_revoked_returns_410(self, authed_client):
        share = SharedReport.create_share(
            tenant=authed_client.tenant,
            dashboard="executive",
        )
        share.revoked_at = timezone.now()
        share.save(update_fields=["revoked_at"])
        from rest_framework.test import APIClient
        public = APIClient()
        resp = public.get(f"/r/{share.token}")
        assert resp.status_code == 410

    def test_invalid_token_404(self):
        from rest_framework.test import APIClient
        public = APIClient()
        resp = public.get("/r/nonexistent-token-abc123")
        assert resp.status_code == 404
