"""
Health checks padrão Kubernetes / load balancers:

- `/healthz` (liveness) — processo está vivo. Sempre rápido, sem DB/Redis.
- `/readyz` (readiness) — pronto pra receber tráfego. Checa DB e Redis (se setado).
- `/api/status` (público, agregado) — para dashboards de status / observabilidade.

Em prod, expor `/healthz` e `/readyz` no load balancer; `/api/status` pode ficar
restrito por IP ou exigir token simples no header (não implementado aqui).
"""
from __future__ import annotations

import platform
import time
from typing import Any

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views import View


def healthz(_request) -> JsonResponse:  # type: ignore[no-untyped-def]
    """Liveness — só responde 200. Não faz I/O."""
    return JsonResponse({"status": "ok"})


def readyz(_request) -> JsonResponse:  # type: ignore[no-untyped-def]
    """Readiness — checa DB e Redis (se setado)."""
    checks: dict[str, Any] = {}
    overall_ok = True

    # DB
    started = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = {
            "ok": True,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "engine": connection.vendor,
        }
    except Exception as e:  # noqa: BLE001
        checks["database"] = {"ok": False, "error": str(e)[:200]}
        overall_ok = False

    # Redis (opcional)
    redis_url = getattr(settings, "REDIS_URL", "")
    if redis_url:
        started = time.perf_counter()
        try:
            import redis  # type: ignore[import-untyped]
            client = redis.from_url(redis_url, socket_timeout=2)
            client.ping()
            checks["redis"] = {
                "ok": True,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        except Exception as e:  # noqa: BLE001
            checks["redis"] = {"ok": False, "error": str(e)[:200]}
            overall_ok = False
    else:
        checks["redis"] = {"ok": True, "skipped": "not_configured"}

    status_code = 200 if overall_ok else 503
    return JsonResponse({"status": "ok" if overall_ok else "degraded", "checks": checks},
                        status=status_code)


class StatusView(View):
    """
    Endpoint público de status. Informa versão, ambiente, integrações ativas.
    Não expõe segredos.
    """

    def get(self, request) -> JsonResponse:  # type: ignore[no-untyped-def]
        from apps.billing.services import get_billing_service

        billing_provider = get_billing_service().name
        contaazul_configured = bool(settings.CONTA_AZUL.get("CLIENT_ID"))

        return JsonResponse({
            "service": "BlueMetrics API",
            "status": "ok",
            "time": timezone.now().isoformat(),
            "version": getattr(settings, "APP_VERSION", "0.1.0"),
            "environment": "debug" if getattr(settings, "DEBUG", False) else "production",
            "python": platform.python_version(),
            "integrations": {
                "billing_provider": billing_provider,
                "contaazul_global_credentials_configured": contaazul_configured,
                "redis_configured": bool(getattr(settings, "REDIS_URL", "")),
                "sentry_configured": bool(getattr(settings, "SENTRY_DSN", "")),
            },
        })
