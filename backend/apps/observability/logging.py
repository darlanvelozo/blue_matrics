"""
Logging estruturado em JSON (sem dependência externa).

Formato:
{"ts": "2026-05-22T12:00:00", "level": "INFO", "logger": "django.request",
 "msg": "GET /api/foo", "request_id": "abc", "tenant_id": 7}

Em produção, agregar via stdout (Cloud Run, Fly.io etc).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Formatter que serializa record + contexto extra como JSON."""

    # Campos sempre incluídos
    _BASE_KEYS = {"ts", "level", "logger", "msg"}
    # Campos opcionais que se existirem no record extra, vão pro JSON
    _EXTRA_KEYS = ("request_id", "tenant_id", "user_id", "path", "method", "status_code")

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k in self._EXTRA_KEYS:
            v = getattr(record, k, None)
            if v is not None:
                payload[k] = v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)
