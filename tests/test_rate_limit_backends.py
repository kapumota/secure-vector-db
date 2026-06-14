from __future__ import annotations

from secure_vector_db.api.rate_limit import (
    DisabledRateLimiter,
    MemoryRateLimiter,
    RedisRateLimiter,
    build_rate_limiter_from_env,
    rate_limiter_backend_info,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


def test_memory_rate_limiter_allows_until_limit() -> None:
    limiter = MemoryRateLimiter(max_requests=2, window_seconds=60)

    first = limiter.allow("cliente", now=100.0)
    second = limiter.allow("cliente", now=101.0)
    third = limiter.allow("cliente", now=102.0)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.backend == "memory"


def test_memory_rate_limiter_resets_after_window() -> None:
    limiter = MemoryRateLimiter(max_requests=1, window_seconds=10)

    assert limiter.allow("cliente", now=100.0).allowed is True
    assert limiter.allow("cliente", now=101.0).allowed is False
    assert limiter.allow("cliente", now=111.0).allowed is True


def test_redis_rate_limiter_uses_shared_counter() -> None:
    fake = FakeRedis()
    limiter = RedisRateLimiter(
        redis_url="redis://example/0",
        max_requests=2,
        window_seconds=60,
        redis_client=fake,
    )

    first = limiter.allow("cliente", now=120.0)
    second = limiter.allow("cliente", now=121.0)
    third = limiter.allow("cliente", now=122.0)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.backend == "redis"
    assert fake.expirations


def test_factory_builds_memory_backend() -> None:
    limiter = build_rate_limiter_from_env(
        {
            "SECURE_VECTOR_DB_RATE_LIMIT_BACKEND": "memory",
            "SECURE_VECTOR_DB_RATE_LIMIT_MAX_REQUESTS": "3",
            "SECURE_VECTOR_DB_RATE_LIMIT_WINDOW_SECONDS": "30",
        }
    )

    assert isinstance(limiter, MemoryRateLimiter)
    assert limiter.max_requests == 3
    assert limiter.window_seconds == 30


def test_factory_builds_disabled_backend() -> None:
    limiter = build_rate_limiter_from_env({"SECURE_VECTOR_DB_RATE_LIMIT_BACKEND": "disabled"})

    assert isinstance(limiter, DisabledRateLimiter)
    assert limiter.allow("cliente").allowed is True


def test_rate_limiter_backend_info_marks_redis_as_distributed() -> None:
    limiter = RedisRateLimiter(
        redis_url="redis://example/0",
        max_requests=1,
        window_seconds=60,
        redis_client=FakeRedis(),
    )

    info = rate_limiter_backend_info(limiter)

    assert info["backend"] == "redis"
    assert info["distributed"] is True
