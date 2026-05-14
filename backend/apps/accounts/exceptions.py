"""Handler de exceções DRF padronizado em JSON."""
from __future__ import annotations

from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):  # type: ignore[no-untyped-def]
    response = exception_handler(exc, context)
    if response is None:
        return response

    # Padroniza para { "error": { "code", "message", "details" } }
    detail = response.data
    code = getattr(exc, "default_code", "error")

    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])
        details = None
    elif isinstance(detail, dict):
        message = "Validação falhou"
        details = detail
    else:
        message = str(detail)
        details = None

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
    return response
