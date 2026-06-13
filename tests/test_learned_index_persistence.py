from __future__ import annotations

import sqlite3

from secure_vector_db.database import SecureVectorDB


def test_persisted_learned_index_survives_reopen(tmp_path) -> None:
    path = tmp_path / "learned.sqlite"

    db = SecureVectorDB.open(path)
    for record_id in range(1, 12):
        db.insert(record_id, f"documento {record_id}")

    train_stats = db.train_learned_index(max_error=0)

    assert train_stats["learned_enabled"] is True
    assert db.ordered_index_stats()["learned_persisted"] is True
    db.close()

    reopened = SecureVectorDB.open(path)
    stats = reopened.ordered_index_stats()
    plan = reopened.explain_search_by_id(5)

    assert stats["learned_enabled"] is True
    assert stats["learned_persisted"] is True
    assert stats["learned_trained_keys"] == 11
    assert plan["strategy"] == "learned_index"
    assert plan["found"] is True

    reopened.close()


def test_persisted_learned_index_is_removed_after_mutation(tmp_path) -> None:
    path = tmp_path / "learned-invalid.sqlite"

    db = SecureVectorDB.open(path)
    for record_id in range(1, 8):
        db.insert(record_id, f"documento {record_id}")

    db.train_learned_index(max_error=0)
    assert db.ordered_index_stats()["learned_persisted"] is True

    db.insert(100, "nuevo documento")
    stats = db.ordered_index_stats()

    assert stats["learned_enabled"] is False
    assert stats["learned_persisted"] is False
    db.close()

    reopened = SecureVectorDB.open(path)
    assert reopened.ordered_index_stats()["learned_enabled"] is False
    assert reopened.search_by_id(3) is not None
    reopened.close()


def test_learned_index_segments_table_is_written(tmp_path) -> None:
    path = tmp_path / "learned-table.sqlite"

    db = SecureVectorDB.open(path)
    for record_id in range(1, 6):
        db.insert(record_id, f"documento {record_id}")
    db.train_learned_index(max_error=0)
    db.close()

    conn = sqlite3.connect(path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM learned_index_segments").fetchone()
        meta = conn.execute(
            "SELECT value FROM kv_meta WHERE key=?",
            ("learned_index:record_id:metadata",),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] >= 1
    assert meta is not None
    assert "key_fingerprint" in meta[0]
