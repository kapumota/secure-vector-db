from __future__ import annotations

from secure_vector_db.api.rate_limit import InMemoryRateLimiter, RateLimitMiddleware


def test_in_memory_rate_limiter_alias_keeps_old_name() -> None:
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)

    assert limiter.is_allowed("cliente", now=100.0) is True
    assert limiter.is_allowed("cliente", now=101.0) is False


def test_in_memory_rate_limiter_accepts_limit_alias() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)

    assert limiter.allow("cliente", now=100.0).allowed is True
    assert limiter.allow("cliente", now=101.0).allowed is False


def test_rate_limit_middleware_is_importable() -> None:
    assert RateLimitMiddleware is not None
