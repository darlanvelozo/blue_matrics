"""Testes de observability."""
from __future__ import annotations

import json
import logging
from io import StringIO

import pytest

from apps.observability.logging import JSONFormatter


class TestJSONFormatter:
    def test_basic_record(self):
        f = JSONFormatter()
        record = logging.LogRecord(
            name="x", level=logging.INFO, pathname="", lineno=0,
            msg="hello %s", args=("world",), exc_info=None,
        )
        out = f.format(record)
        d = json.loads(out)
        assert d["msg"] == "hello world"
        assert d["level"] == "INFO"
        assert d["logger"] == "x"
        assert "ts" in d

    def test_with_extra_fields(self):
        f = JSONFormatter()
        record = logging.LogRecord(
            name="x", level=logging.INFO, pathname="", lineno=0,
            msg="foo", args=(), exc_info=None,
        )
        record.request_id = "abc123"
        record.tenant_id = 7
        record.path = "/api/foo"
        out = f.format(record)
        d = json.loads(out)
        assert d["request_id"] == "abc123"
        assert d["tenant_id"] == 7
        assert d["path"] == "/api/foo"

    def test_handles_exception(self):
        f = JSONFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="x", level=logging.ERROR, pathname="", lineno=0,
                msg="failed", args=(), exc_info=sys.exc_info(),
            )
        d = json.loads(f.format(record))
        assert "exc" in d
        assert "ValueError" in d["exc"]


class TestHealthz:
    URL = "/healthz"

    def test_returns_200(self, api_client):
        r = api_client.get(self.URL)
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.django_db
class TestReadyz:
    URL = "/readyz"

    def test_db_ok(self, api_client):
        r = api_client.get(self.URL)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["checks"]["database"]["ok"] is True
        assert "latency_ms" in body["checks"]["database"]
        # redis "skipped" em dev
        assert body["checks"]["redis"]["ok"] is True


class TestStatusView:
    URL = "/api/status"

    def test_public_no_secrets(self, api_client):
        r = api_client.get(self.URL)
        assert r.status_code == 200
        body = r.json()
        assert body["service"] == "BlueMetrics API"
        assert "integrations" in body
        # nenhum segredo
        s = json.dumps(body)
        assert "secret" not in s.lower()
        assert "fernet" not in s.lower()
        assert "client_secret" not in s.lower()


class TestRequestIdEcho:
    def test_echoes_x_request_id(self, api_client):
        r = api_client.get("/api/status", HTTP_X_REQUEST_ID="my-trace-123")
        assert r["X-Request-ID"] == "my-trace-123"

    def test_generates_when_missing(self, api_client):
        r = api_client.get("/api/status")
        assert "X-Request-ID" in r
        assert len(r["X-Request-ID"]) >= 16


def test_json_formatter_serializable():
    """Sanity check: usado pelo settings de prod via LOGGING dict-config."""
    out = StringIO()
    handler = logging.StreamHandler(out)
    handler.setFormatter(JSONFormatter())
    log = logging.getLogger("test-obs-fmt")
    log.handlers = [handler]
    log.setLevel(logging.INFO)
    log.info("hi", extra={"request_id": "r1"})
    line = out.getvalue().strip()
    json.loads(line)  # válido
