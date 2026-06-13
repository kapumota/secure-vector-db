from __future__ import annotations

from fastapi.testclient import TestClient

from secure_vector_db.api.auth import DEFAULT_DEV_API_KEY
from secure_vector_db.api.server import app
from secure_vector_db.database import SecureVectorDB


def test_database_trains_and_uses_hybrid_ordered_index() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 8):
        db.insert(record_id, f"documento {record_id}", {"grupo": "fase2"})

    stats = db.train_learned_index(max_error=0)

    assert stats["learned_enabled"] is True
    assert stats["learned_segments"] == 1
    assert db.search_by_id(5) is not None

    fallback_before = db.ordered_index_stats()["learned_fallback_count"]
    assert db.search_by_id(1000) is None
    fallback_after = db.ordered_index_stats()["learned_fallback_count"]

    assert fallback_after == fallback_before + 1


def test_database_disables_learned_index_after_insert_or_delete() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 5):
        db.insert(record_id, f"documento {record_id}")

    db.train_learned_index(max_error=0)
    assert db.ordered_index_stats()["learned_enabled"] is True

    db.insert(10, "nuevo documento")
    assert db.ordered_index_stats()["learned_enabled"] is False

    db.train_learned_index(max_error=1)
    assert db.ordered_index_stats()["learned_enabled"] is True

    assert db.delete(10) is True
    assert db.ordered_index_stats()["learned_enabled"] is False


def test_database_can_open_with_learned_index_enabled(tmp_path) -> None:
    path = tmp_path / "learned.sqlite"

    db = SecureVectorDB.open(path)
    for record_id in range(1, 6):
        db.insert(record_id, f"persistente {record_id}")
    db.close()

    reopened = SecureVectorDB.open(path, learned_index_enabled=True, learned_max_error=0)

    assert reopened.ordered_index_stats()["learned_enabled"] is True
    assert reopened.search_by_id(3) is not None

    reopened.close()


def test_ordered_index_stats_endpoint(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SECURE_VECTOR_DB_PATH", str(tmp_path / "api-learned.sqlite"))
    monkeypatch.setenv("SECURE_VECTOR_DB_LEARNED_INDEX", "true")
    monkeypatch.setenv("SECURE_VECTOR_DB_LEARNED_MAX_ERROR", "4")
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEY", raising=False)

    with TestClient(app) as client:
        headers = {"X-API-Key": DEFAULT_DEV_API_KEY}
        response = client.get("/indexes/ordered/stats", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert "learned_enabled" in payload
        assert "learned_fallback_count" in payload
        assert "learned_fallback_rate" in payload
