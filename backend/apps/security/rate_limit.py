"""
Rate limit simples in-memory (sliding window por chave).

Em produção troca por Redis (RedisCacheRateLimit) — o protocolo é o mesmo.
"""
from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Protocol

from rest_framework.exceptions import Throttled


class RateLimiter(Protocol):
    def check(self, key: str, *, limit: int, window_seconds: int) -> int: ...


class InMemoryRateLimiter:
    """Sliding window por chave. Thread-safe via Lock."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> int:
        """
        Retorna a contagem atual após registrar este hit.
        Lança `Throttled` se exceder.
        """
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._hits.setdefault(key, deque())
            # drop antigos
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                wait = max(1, int(q[0] + window_seconds - now))
                raise Throttled(wait=wait, detail=f"Limite atingido: {limit}/{window_seconds}s")
            q.append(now)
            return len(q)


# singleton de processo
_default = InMemoryRateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _default


# ---------------------------------------------------------------------------
# Decorator pra views DRF
# ---------------------------------------------------------------------------
def rate_limit(*, key_prefix: str, limit: int, window_seconds: int = 60):
    """
    Aplica em views DRF (function-based ou .post/.get de APIView).
    Chave: prefix + (user_id ou ip).
    """
    def decorator(view_func):  # type: ignore[no-untyped-def]
        from functools import wraps

        @wraps(view_func)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            # `args` é (self, request) em method ou (request,) em function-based
            request = args[1] if len(args) > 1 else args[0]
            user_id = getattr(getattr(request, "user", None), "id", None)
            ip = request.META.get("REMOTE_ADDR", "0.0.0.0")  # noqa: S104
            key = f"{key_prefix}:{user_id or 'anon-' + ip}"
            get_rate_limiter().check(key, limit=limit, window_seconds=window_seconds)
            return view_func(*args, **kwargs)
        return wrapper
    return decorator


def reset_rate_limiter() -> None:
    """Limpa todos os hits — uso em testes."""
    global _default
    _default = InMemoryRateLimiter()
