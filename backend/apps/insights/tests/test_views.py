"""Testes das views de insights."""
from __future__ import annotations

from datetime import date

import pytest

from apps.insights.models import Insight


@pytest.mark.django_db
class TestListInsights:
    URL = "/api/insights/"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_empty(self, authed_client):
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"insights": [], "unread": 0, "total": 0}

    def test_returns_only_own_tenant(self, authed_client, make_tenant):
        other = make_tenant("other")
        Insight.unsafe_objects.create(
            tenant_id=other.id, kind="revenue_drop", severity="warning",
            title="leak?", narrative="", period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
        )
        Insight.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, kind="revenue_drop",
            severity="warning", title="meu insight", narrative="",
            period_start=date(2026, 4, 1), period_end=date(2026, 4, 30),
        )

        body = authed_client.get(self.URL).json()
        assert body["total"] == 1
        assert body["insights"][0]["title"] == "meu insight"

    def test_dismissed_not_returned(self, authed_client):
        from django.utils import timezone
        i = Insight.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, kind="revenue_drop",
            severity="warning", title="x", narrative="",
            period_start=date(2026, 4, 1), period_end=date(2026, 4, 30),
        )
        i.dismissed_at = timezone.now()
        i.save()
        body = authed_client.get(self.URL).json()
        assert body["total"] == 0


@pytest.mark.django_db
class TestGenerate:
    URL = "/api/insights/generate"

    def test_requires_auth(self, api_client):
        assert api_client.post(self.URL).status_code == 401

    def test_returns_stats(self, authed_client):
        resp = authed_client.post(self.URL)
        assert resp.status_code == 202
        body = resp.json()
        assert "stats" in body
        assert "candidates" in body["stats"]


@pytest.mark.django_db
class TestMarkReadDismiss:
    def test_mark_read(self, authed_client):
        i = Insight.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, kind="revenue_drop",
            severity="info", title="x", narrative="",
            period_start=date(2026, 4, 1), period_end=date(2026, 4, 30),
        )
        resp = authed_client.post(f"/api/insights/{i.id}/read")
        assert resp.status_code == 200
        assert resp.json()["is_read"] is True

    def test_dismiss(self, authed_client):
        i = Insight.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, kind="revenue_drop",
            severity="info", title="x", narrative="",
            period_start=date(2026, 4, 1), period_end=date(2026, 4, 30),
        )
        resp = authed_client.post(f"/api/insights/{i.id}/dismiss")
        assert resp.status_code == 200
        assert resp.json() == {"dismissed": True}
        i.refresh_from_db()
        assert i.dismissed_at is not None

    def test_dismiss_404_for_other_tenant(self, authed_client, make_tenant):
        other = make_tenant("other")
        i = Insight.unsafe_objects.create(
            tenant_id=other.id, kind="revenue_drop",
            severity="info", title="x", narrative="",
            period_start=date(2026, 4, 1), period_end=date(2026, 4, 30),
        )
        resp = authed_client.post(f"/api/insights/{i.id}/dismiss")
        assert resp.status_code == 404
