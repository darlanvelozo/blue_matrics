"""Testes da task refresh_expiring_tokens."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from apps.integrations.models import ContaAzulConnection
from apps.integrations.services import OAuthError, OAuthTokens
from apps.integrations.tasks import refresh_expiring_tokens


@pytest.mark.django_db
class TestRefreshTask:
    def _make_connected(self, tenant, *, minutes_to_expire: int):
        conn = ContaAzulConnection.objects.create(tenant=tenant)
        conn.set_access_token("old-access", expires_in=minutes_to_expire * 60)
        conn.set_refresh_token("old-refresh")
        conn.mark_connected()
        conn.save()
        return conn

    @patch("apps.integrations.tasks.ContaAzulOAuthService")
    def test_refreshes_expiring(self, mock_service_cls, make_tenant):
        t1 = make_tenant("expires-soon")
        t2 = make_tenant("expires-later")
        self._make_connected(t1, minutes_to_expire=2)
        self._make_connected(t2, minutes_to_expire=60)

        mock_service_cls.for_connection.return_value.refresh.return_value = OAuthTokens(
            access_token="new-acc",
            refresh_token="new-ref",
            expires_in=3600,
            scope="openid",
        )

        stats = refresh_expiring_tokens(window_minutes=10)
        assert stats == {"checked": 1, "refreshed": 1, "failed": 0}

        c1 = ContaAzulConnection.objects.get(tenant=t1)
        assert c1.access_token == "new-acc"
        assert c1.refresh_token == "new-ref"
        assert c1.status == ContaAzulConnection.Status.CONNECTED

        # t2 (longe de expirar) não foi tocado
        c2 = ContaAzulConnection.objects.get(tenant=t2)
        assert c2.access_token == "old-access"

    @patch("apps.integrations.tasks.ContaAzulOAuthService")
    def test_marks_error_when_refresh_fails(self, mock_service_cls, make_tenant):
        t = make_tenant()
        self._make_connected(t, minutes_to_expire=1)
        mock_service_cls.for_connection.return_value.refresh.side_effect = OAuthError("nope")

        stats = refresh_expiring_tokens(window_minutes=10)
        assert stats["failed"] == 1
        conn = ContaAzulConnection.objects.get(tenant=t)
        assert conn.status == ContaAzulConnection.Status.ERROR
        assert "nope" in conn.last_error

    def test_skips_connection_without_refresh_token(self, make_tenant):
        t = make_tenant()
        conn = ContaAzulConnection.objects.create(tenant=t)
        conn.set_access_token("x", expires_in=60)
        conn.mark_connected()
        conn.save()

        stats = refresh_expiring_tokens(window_minutes=10)
        assert stats["failed"] == 1
        conn.refresh_from_db()
        assert conn.status == ContaAzulConnection.Status.ERROR

    def test_returns_zero_when_nothing_expires(self, make_tenant):
        t = make_tenant()
        # status default = disconnected; não entra no qs
        ContaAzulConnection.objects.create(tenant=t)
        # uma conectada que expira longe
        t2 = make_tenant("ok")
        self._make_connected(t2, minutes_to_expire=120)

        stats = refresh_expiring_tokens(window_minutes=10)
        assert stats == {"checked": 0, "refreshed": 0, "failed": 0}

    def test_expires_at_advances_with_skew(self, make_tenant):
        """expires_at antigo + janela de skew_seconds → re-saves a campo."""
        t = make_tenant()
        conn = self._make_connected(t, minutes_to_expire=1)
        # before: ~ now + 60s
        before = conn.expires_at

        with patch("apps.integrations.tasks.ContaAzulOAuthService") as svc_cls:
            svc_cls.for_connection.return_value.refresh.return_value = OAuthTokens(
                access_token="A", refresh_token="R", expires_in=3600, scope=""
            )
            refresh_expiring_tokens(window_minutes=10)

        conn.refresh_from_db()
        assert conn.expires_at > before + timedelta(minutes=30)
