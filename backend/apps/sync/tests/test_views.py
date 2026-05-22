"""Testes dos endpoints /api/sync/*."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.integrations.models import ContaAzulConnection
from apps.sync.models import SyncLog


@pytest.mark.django_db
class TestLogsView:
    URL = "/api/sync/logs"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_returns_empty_when_no_logs(self, authed_client):
        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json() == {"logs": []}

    def test_returns_logs_only_from_tenant(self, authed_client, make_tenant):
        other = make_tenant("other")
        SyncLog.objects.create(tenant=other, resource="sales", status="success")
        SyncLog.objects.create(tenant=authed_client.tenant, resource="sales", status="success")

        body = authed_client.get(self.URL).json()
        assert len(body["logs"]) == 1
        assert body["logs"][0]["resource"] == "sales"


@pytest.mark.django_db
class TestRunNowView:
    URL = "/api/sync/run"

    def test_requires_auth(self, api_client):
        assert api_client.post(self.URL).status_code == 401

    def test_400_if_not_connected(self, authed_client):
        # sem ContaAzulConnection
        resp = authed_client.post(self.URL)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "not_connected"

    def test_400_if_connection_disconnected(self, authed_client):
        ContaAzulConnection.objects.create(tenant=authed_client.tenant)  # disconnected
        resp = authed_client.post(self.URL)
        assert resp.status_code == 400

    @patch("apps.sync.views.sync_tenant_task.apply")
    def test_queues_task(self, mock_apply, authed_client):
        # Em testes, CELERY_TASK_ALWAYS_EAGER=True → view chama .apply() (não .delay()).
        from django.utils import timezone
        conn = ContaAzulConnection.objects.create(tenant=authed_client.tenant)
        conn.set_access_token("x", expires_in=3600)
        conn.mark_connected()
        conn.save()
        mock_apply.return_value.id = "task-uuid-123"

        resp = authed_client.post(self.URL)
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "done"  # eager mode em testes
        assert body["task_id"] == "task-uuid-123"
        mock_apply.assert_called_once_with(args=[authed_client.tenant.id])
        _ = timezone  # quiet linter
