"""Backends de rate limiting para API."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Mapping, MutableMapping, Optional, Protocol, runtime_checkable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@dataclass(frozen=True)
class RateLimitDecision:
    """Resultado de una evaluacion de rate limit."""

    allowed: bool
    remaining: int
    reset_seconds: int
    backend: str
    key: str

    def __getitem__(self, index: int) -> bool | int | str:
        """Permite acceso compatible con tuplas usadas por tests antiguos."""
        values: tuple[bool | int | str, ...] = (
            self.allowed,
            self.remaining,
            self.reset_seconds,
            self.backend,
            self.key,
        )
        return values[index]

    def __iter__(self):
        """Permite desempaquetar la decision como tupla antigua."""
        yield self.allowed
        yield self.remaining
        yield self.reset_seconds


@runtime_checkable
class RateLimiterBackend(Protocol):
    """Contrato comun para backends de rate limiting."""

    name: str

    def allow(self, identifier: str, now: Optional[float] = None) -> RateLimitDecision:
        """Evalua si un identificador puede continuar."""


class MemoryRateLimiter:
    """Rate limiter en memoria para demo local y pruebas."""

    name = "memory"

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests debe ser mayor que cero")
        if window_seconds <= 0:
            raise ValueError("window_seconds debe ser mayor que cero")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: MutableMapping[str, list[float]] = {}
        self._lock = Lock()

    def allow(self, identifier: str, now: Optional[float] = None) -> RateLimitDecision:
        """Evalua rate limit usando ventana deslizante local."""
        current = time.time() if now is None else float(now)
        window_start = current - self.window_seconds
        key = identifier or "unknown"

        with self._lock:
            events = [value for value in self._events.get(key, []) if value > window_start]
            allowed = len(events) < self.max_requests
            if allowed:
                events.append(current)
            self._events[key] = events

            remaining = max(0, self.max_requests - len(events))
            oldest = min(events) if events else current
            reset_seconds = max(0, int(self.window_seconds - (current - oldest)))

        return RateLimitDecision(
            allowed=allowed,
            remaining=remaining,
            reset_seconds=reset_seconds,
            backend=self.name,
            key=key,
        )


class RedisRateLimiter:
    """Rate limiter distribuido con Redis."""

    name = "redis"

    def __init__(
        self,
        redis_url: str,
        max_requests: int = 60,
        window_seconds: int = 60,
        prefix: str = "svdb:rate_limit",
        redis_client: Any | None = None,
    ) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests debe ser mayor que cero")
        if window_seconds <= 0:
            raise ValueError("window_seconds debe ser mayor que cero")

        self.redis_url = redis_url
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix

        if redis_client is not None:
            self._client = redis_client
        else:
            try:
                import redis  # type: ignore[import-untyped]
            except ImportError as exc:
                raise RuntimeError(
                    "redis no esta instalado. Instala requirements-redis.txt para usar este backend."
                ) from exc
            self._client = redis.from_url(redis_url, decode_responses=True)

    def allow(self, identifier: str, now: Optional[float] = None) -> RateLimitDecision:
        """Evalua rate limit usando contador compartido en Redis."""
        current = int(time.time() if now is None else float(now))
        key_id = identifier or "unknown"
        window_id = current // self.window_seconds
        redis_key = f"{self.prefix}:{key_id}:{window_id}"

        count = int(self._client.incr(redis_key))
        if count == 1:
            self._client.expire(redis_key, self.window_seconds)

        allowed = count <= self.max_requests
        remaining = max(0, self.max_requests - count)
        reset_seconds = self.window_seconds - (current % self.window_seconds)

        return RateLimitDecision(
            allowed=allowed,
            remaining=remaining,
            reset_seconds=reset_seconds,
            backend=self.name,
            key=key_id,
        )


class DisabledRateLimiter:
    """Rate limiter desactivado para pruebas controladas."""

    name = "disabled"

    def allow(self, identifier: str, now: Optional[float] = None) -> RateLimitDecision:
        """Permite siempre la solicitud."""
        key = identifier or "unknown"
        return RateLimitDecision(
            allowed=True,
            remaining=2_147_483_647,
            reset_seconds=0,
            backend=self.name,
            key=key,
        )


def build_rate_limiter_from_env(env: Optional[Mapping[str, str]] = None) -> RateLimiterBackend:
    """Construye backend de rate limiting desde variables de entorno."""
    source = os.environ if env is None else env
    backend = source.get("SECURE_VECTOR_DB_RATE_LIMIT_BACKEND", "memory").strip().lower()
    max_requests = int(source.get("SECURE_VECTOR_DB_RATE_LIMIT_MAX_REQUESTS", "60"))
    window_seconds = int(source.get("SECURE_VECTOR_DB_RATE_LIMIT_WINDOW_SECONDS", "60"))

    if backend == "memory":
        return MemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)
    if backend == "redis":
        redis_url = source.get("SECURE_VECTOR_DB_RATE_LIMIT_REDIS_URL", "redis://localhost:6379/0")
        return RedisRateLimiter(
            redis_url=redis_url,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
    if backend == "disabled":
        return DisabledRateLimiter()

    raise ValueError(f"backend de rate limiting no soportado: {backend}")


def rate_limiter_backend_info(backend: RateLimiterBackend) -> dict[str, Any]:
    """Devuelve informacion segura del backend configurado."""
    return {
        "backend": backend.name,
        "distributed": backend.name == "redis",
        "status": "active",
    }



class InMemoryRateLimiter(MemoryRateLimiter):
    """Alias compatible para el rate limiter anterior en memoria."""

    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        limit: int | None = None,
    ) -> None:
        # Mantiene compatibilidad con codigo anterior que usaba limit.
        effective_limit = max_requests if limit is None else limit
        super().__init__(max_requests=effective_limit, window_seconds=window_seconds)

    def is_allowed(self, identifier: str, now: Optional[float] = None) -> bool:
        """Devuelve solo decision booleana para compatibilidad."""
        return self.allow(identifier, now=now).allowed




class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware compatible para aplicar rate limiting configurable."""

    def __init__(
        self,
        app: Any,
        limiter: RateLimiterBackend | None = None,
        max_requests: int | None = None,
        window_seconds: int | None = None,
    ) -> None:
        super().__init__(app)
        if limiter is not None:
            self.limiter = limiter
        elif max_requests is not None or window_seconds is not None:
            self.limiter = MemoryRateLimiter(
                max_requests=max_requests or 60,
                window_seconds=window_seconds or 60,
            )
        else:
            self.limiter = build_rate_limiter_from_env()

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Evalua rate limit antes de continuar la solicitud."""
        client = getattr(request, "client", None)
        identifier = client.host if client else "unknown"
        decision = self.limiter.allow(identifier)

        if not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "limite de tasa excedido",
                    "backend": decision.backend,
                    "reset_seconds": decision.reset_seconds,
                },
                headers={
                    "Retry-After": str(decision.reset_seconds),
                    "X-RateLimit-Remaining": str(decision.remaining),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Backend"] = decision.backend
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        return response
