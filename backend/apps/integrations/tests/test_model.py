"""Testes do model ContaAzulConnection."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.integrations.models import ContaAzulConnection


@pytest.mark.django_db
class TestConnectionModel:
    def test_set_tokens_encrypts(self, make_tenant):
        t = make_tenant()
        conn = ContaAzulConnection.objects.create(tenant=t)
        conn.set_access_token("plain-access", expires_in=3600)
        conn.set_refresh_token("plain-refresh")
        conn.save()
        conn.refresh_from_db()

        # ciphertext != plaintext
        assert conn.access_token_enc != "plain-access"
        assert conn.refresh_token_enc != "plain-refresh"
        # properties decifram
        assert conn.access_token == "plain-access"
        assert conn.refresh_token == "plain-refresh"

    def test_is_expired(self, make_tenant):
        t = make_tenant()
        conn = ContaAzulConnection.objects.create(tenant=t)
        # sem expires_at → expirado
        assert conn.is_expired() is True

        conn.expires_at = timezone.now() + timedelta(minutes=10)
        assert conn.is_expired() is False

        conn.expires_at = timezone.now() - timedelta(seconds=1)
        assert conn.is_expired() is True

    def test_mark_connected_clears_error(self, make_tenant):
        t = make_tenant()
        conn = ContaAzulConnection.objects.create(tenant=t)
        conn.mark_error("falhou")
        conn.save()
        assert conn.status == ContaAzulConnection.Status.ERROR
        assert "falhou" in conn.last_error

        conn.mark_connected()
        conn.save()
        assert conn.status == ContaAzulConnection.Status.CONNECTED
        assert conn.last_error == ""
        assert conn.connected_at is not None
