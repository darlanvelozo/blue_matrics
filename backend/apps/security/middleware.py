"""
Security headers — defesa em profundidade no nível HTTP.

Aplica em TODAS as respostas. Em dev é menos restritivo (sem HSTS, CSP relaxado).
"""
from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse


class SecurityHeadersMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.debug = getattr(settings, "DEBUG", False)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        # Sempre aplicados
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("X-Frame-Options", "DENY")
        # Em produção também: HSTS (Django já cuida via SECURE_HSTS_*) e CSP
        if not self.debug:
            response.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data: https:; "
                "script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' https://api-v2.contaazul.com https://auth.contaazul.com; "
                "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            )
        return response
