"""
Middleware que adiciona `request_id` único ao request e loga cada response.

Header `X-Request-ID` pode ser passado pelo cliente (ex: load balancer) ou
geramos um UUID novo. Vai pro log e na resposta como echo.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("bluemetrics.request")


class RequestLogMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = (
            request.META.get("HTTP_X_REQUEST_ID")
            or uuid.uuid4().hex[:16]
        )
        request.request_id = request_id  # type: ignore[attr-defined]

        started = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        response["X-Request-ID"] = request_id

        # Pula log de health checks (ruído)
        path = request.path
        if not (path.startswith("/healthz") or path.startswith("/readyz")):
            user = getattr(request, "user", None)
            user_id = user.id if user and getattr(user, "is_authenticated", False) else None
            tenant = getattr(request, "tenant", None)
            tenant_id = tenant.id if tenant else None
            logger.info(
                "%s %s → %s (%.1fms)",
                request.method, path, response.status_code, elapsed_ms,
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "path": path,
                    "method": request.method,
                    "status_code": response.status_code,
                },
            )
        return response
