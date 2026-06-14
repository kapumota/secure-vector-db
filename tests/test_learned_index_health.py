from __future__ import annotations

from secure_vector_db.database import SecureVectorDB
from secure_vector_db.indexes.learned_index_health import evaluate_learned_index_health


def test_learned_index_health_needs_retrain_without_model() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 6):
        db.insert(record_id, f"documento {record_id}")

    health = db.learned_index_health()

    assert health["status"] == "needs_retrain"
    assert health["recommendation"] == "retrain"
    assert health["learned_enabled"] is False
    assert health["current_key_count"] == 5


def test_learned_index_health_is_healthy_after_training() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 10):
        db.insert(record_id, f"documento {record_id}")

    db.train_learned_index(max_error=4)
    health = db.learned_index_health()

    assert health["status"] == "healthy"
    assert health["recommendation"] == "keep"
    assert health["learned_enabled"] is True
    assert health["trained_key_count"] == 9
    assert health["current_key_count"] == 9


def test_learned_index_health_needs_retrain_after_insert() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 6):
        db.insert(record_id, f"documento {record_id}")

    db.train_learned_index(max_error=4)
    db.insert(99, "documento nuevo")
    health = db.learned_index_health()

    assert health["status"] == "needs_retrain"
    assert health["recommendation"] == "retrain"
    assert health["learned_enabled"] is False
    assert health["inserts_since_training"] == 6


def test_retrain_learned_index_restores_health() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 6):
        db.insert(record_id, f"documento {record_id}")

    db.train_learned_index(max_error=4)
    db.insert(99, "documento nuevo")

    result = db.retrain_learned_index(max_error=4)

    assert result["health"]["status"] == "healthy"
    assert result["health"]["learned_enabled"] is True
    assert result["health"]["current_key_count"] == 6


def test_health_policy_marks_high_fallback_as_degraded() -> None:
    stats = {
        "learned_enabled": True,
        "learned_persisted": True,
        "learned_trained_keys": 10,
        "learned_fallback_rate": 0.50,
        "learned_max_error": 1,
        "learned_avg_error": 0.1,
        "learned_configured_max_error": 4,
        "learned_disabled_reason": "",
    }

    health = evaluate_learned_index_health(stats, current_key_count=10, fallback_threshold=0.20)

    assert health["status"] == "degraded"
    assert health["recommendation"] == "retrain"
    assert health["needs_retrain"] is True
