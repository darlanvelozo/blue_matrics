"""Testes dos endpoints /api/goals."""
from __future__ import annotations

from decimal import Decimal

import pytest

from apps.goals.models import Goal


@pytest.mark.django_db
class TestGoalsList:
    URL = "/api/goals/"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_lists_only_own_tenant(self, authed_client, make_tenant):
        Goal.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, name="Mine",
            kind=Goal.Kind.REVENUE, period=Goal.Period.MONTH,
            target_value=Decimal("1000"),
        )
        other = make_tenant("other")
        Goal.unsafe_objects.create(
            tenant_id=other.id, name="Theirs",
            kind=Goal.Kind.REVENUE, period=Goal.Period.MONTH,
            target_value=Decimal("9999"),
        )
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        names = [g["name"] for g in resp.json()["goals"]]
        assert "Mine" in names
        assert "Theirs" not in names

    def test_create(self, authed_client):
        resp = authed_client.post(self.URL, {
            "name": "Faturar 10k em abril",
            "kind": "revenue",
            "period": "month",
            "target_value": 10000,
        }, format="json")
        assert resp.status_code == 201, resp.content
        d = resp.json()
        assert d["name"] == "Faturar 10k em abril"
        assert d["kind"] == "revenue"
        assert d["target_value"] == 10000.0
        assert "progress" in d

    def test_validation_invalid_kind(self, authed_client):
        resp = authed_client.post(self.URL, {
            "name": "x", "kind": "bogus", "target_value": 100,
        }, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_kind"

    def test_validation_target_zero(self, authed_client):
        resp = authed_client.post(self.URL, {
            "name": "x", "kind": "revenue", "target_value": 0,
        }, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_target"

    def test_validation_missing_name(self, authed_client):
        resp = authed_client.post(self.URL, {
            "name": "", "kind": "revenue", "target_value": 100,
        }, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "missing_name"


@pytest.mark.django_db
class TestGoalDetail:
    def _url(self, pk: int) -> str:
        return f"/api/goals/{pk}"

    def test_patch(self, authed_client):
        g = Goal.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, name="old",
            kind=Goal.Kind.REVENUE, period=Goal.Period.MONTH,
            target_value=Decimal("100"),
        )
        resp = authed_client.patch(self._url(g.id), {
            "name": "novo nome", "target_value": 500,
        }, format="json")
        assert resp.status_code == 200
        g.refresh_from_db()
        assert g.name == "novo nome"
        assert g.target_value == Decimal("500.00")

    def test_delete(self, authed_client):
        g = Goal.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, name="x",
            kind=Goal.Kind.REVENUE, period=Goal.Period.MONTH,
            target_value=Decimal("100"),
        )
        resp = authed_client.delete(self._url(g.id))
        assert resp.status_code == 204
        assert Goal.unsafe_objects.filter(id=g.id).count() == 0

    def test_404_other_tenant(self, authed_client, make_tenant):
        other = make_tenant("other")
        g = Goal.unsafe_objects.create(
            tenant_id=other.id, name="x",
            kind=Goal.Kind.REVENUE, period=Goal.Period.MONTH,
            target_value=Decimal("100"),
        )
        resp = authed_client.get(self._url(g.id))
        assert resp.status_code == 404
