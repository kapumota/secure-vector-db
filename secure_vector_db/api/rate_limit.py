from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import RLock
from typing import Deque, DefaultDict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

RATE_LIMIT_ENV = "SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE"
DEFAULT_RATE_LIMIT_PER_MINUTE = 120


class InMemoryRateLimiter:
    """Limitador de ventana deslizante seguro para subprocesos, para implementaciones sencillas de un solo proceso."""

    def __init__(self, max_requests: int = DEFAULT_RATE_LIMIT_PER_MINUTE, window_seconds: int = 60):
        if max_requests <= 0:
            raise ValueError("max_requests debe ser positivo")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._lock = RLock()

    def allow(self, key: str, now: float | None = None) -> tuple[bool, int, float]:
        current = time.monotonic() if now is None else now
        cutoff = current - self.window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            remaining = max(self.max_requests - len(bucket), 0)
            if len(bucket) >= self.max_requests:
                retry_after = max(bucket[0] + self.window_seconds - current, 0.0)
                return False, 0, retry_after
            bucket.append(current)
            return True, remaining - 1, 0.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware FastAPI/Starlette con limitación de velocidad por IP de cliente."""

    def __init__(self, app, limiter: InMemoryRateLimiter | None = None):
        max_requests = int(os.environ.get(RATE_LIMIT_ENV, str(DEFAULT_RATE_LIMIT_PER_MINUTE)))
        super().__init__(app)
        self.limiter = limiter or InMemoryRateLimiter(max_requests=max_requests)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in {"/health", "/openapi.json", "/docs", "/redoc"}:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        api_key = request.headers.get("X-API-Key", "anonymous")
        key = f"{client_host}:{api_key}"
        allowed, remaining, retry_after = self.limiter.allow(key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "RateLimitExceeded", "detail": "Demasiadas solicitudes. Intente nuevamente más tarde."},
                headers={"Retry-After": str(int(retry_after) + 1), "X-RateLimit-Remaining": "0"},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(max(remaining, 0))
        return response
