from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_rate_limiting_doc_mentions_memory_and_redis() -> None:
    text = (ROOT / "docs" / "RATE_LIMITING.md").read_text(encoding="utf-8")

    assert "MemoryRateLimiter" in text
    assert "RedisRateLimiter" in text
    assert "SECURE_VECTOR_DB_RATE_LIMIT_BACKEND=redis" in text


def test_security_baseline_mentions_redis_backend() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "RedisRateLimiter" in text
    assert "rate limiting distribuido" in text


def test_deployment_security_mentions_redis_backend() -> None:
    text = (ROOT / "docs" / "DEPLOYMENT_SECURITY.md").read_text(encoding="utf-8")

    assert "SECURE_VECTOR_DB_RATE_LIMIT_BACKEND=redis" in text
    assert "Redis" in text
