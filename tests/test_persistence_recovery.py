from __future__ import annotations

import sqlite3
from pathlib import Path

from secure_vector_db.database import SecureVectorDB


def test_reopen_preserves_records_and_root(tmp_path: Path) -> None:
    db_path = tmp_path / "recovery.sqlite"

    db = SecureVectorDB.open(db_path)
    for record_id in range(1, 8):
        db.insert(record_id, f"documento {record_id}", {"grupo": "persistencia"})

    root_before = db.root_hash
    db.close()

    reopened = SecureVectorDB.open(db_path)

    assert reopened.verify_dataset() is True
    assert reopened.root_hash == root_before
    assert reopened.search_by_id(3) is not None
    assert reopened.search_by_range(2, 5)[0].record_id == 2
    assert reopened.persistence_health()["status"] == "healthy"

    reopened.close()


def test_delete_reopen_preserves_merkle_root(tmp_path: Path) -> None:
    db_path = tmp_path / "delete-recovery.sqlite"

    db = SecureVectorDB.open(db_path)
    for record_id in range(1, 6):
        db.insert(record_id, f"documento {record_id}")

    assert db.delete(3) is True
    root_after_delete = db.root_hash
    db.close()

    reopened = SecureVectorDB.open(db_path)

    assert reopened.search_by_id(3) is None
    assert reopened.verify_dataset() is True
    assert reopened.root_hash == root_after_delete
    assert reopened.persistence_health()["root_matches"] is True

    reopened.close()


def test_learned_index_segments_survive_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "learned-recovery.sqlite"

    db = SecureVectorDB.open(db_path)
    for record_id in range(1, 64):
        db.insert(record_id, f"documento {record_id}")

    db.retrain_learned_index(max_error=8)
    health_before = db.learned_index_health()
    db.close()

    reopened = SecureVectorDB.open(db_path)
    health_after = reopened.learned_index_health()

    assert health_before["learned_enabled"] is True
    assert health_after["learned_enabled"] is True
    assert health_after["learned_persisted"] is True
    assert health_after["status"] == "healthy"
    assert reopened.explain_record(20)["primary_index"] == "learned_piecewise_index"

    reopened.close()


def test_incompatible_learned_metadata_does_not_break_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "bad-metadata.sqlite"

    db = SecureVectorDB.open(db_path)
    for record_id in range(1, 32):
        db.insert(record_id, f"documento {record_id}")

    db.retrain_learned_index(max_error=8)
    db.close()

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT key, value FROM kv_meta WHERE key LIKE 'learned_index:%:metadata' LIMIT 1"
        ).fetchone()
        assert row is not None
        conn.execute("UPDATE kv_meta SET value=? WHERE key=?", ("{}", row[0]))

    reopened = SecureVectorDB.open(db_path)
    health = reopened.learned_index_health()

    assert reopened.verify_dataset() is True
    assert health["learned_enabled"] is False
    assert health["persisted_model_valid"] is False
    assert reopened.search_by_id(10) is not None

    reopened.close()


def test_auxiliary_indexes_rebuild_from_sqlite_records(tmp_path: Path) -> None:
    db_path = tmp_path / "rebuild-indexes.sqlite"

    db = SecureVectorDB.open(db_path)
    for record_id in range(10, 21):
        db.insert(record_id, f"texto semantico {record_id}", {"tipo": "rebuild"})
    db.close()

    reopened = SecureVectorDB.open(db_path)

    by_id = reopened.search_by_id(15)
    by_range = reopened.search_by_range(12, 14)
    semantic = reopened.semantic_search("texto semantico", k=3)

    assert by_id is not None
    assert [record.record_id for record in by_range] == [12, 13, 14]
    assert len(semantic) == 3
    assert reopened.persistence_health()["source_of_truth"] == "sqlite_records"

    reopened.close()


def test_empty_database_reopens_cleanly(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.sqlite"

    db = SecureVectorDB.open(db_path)
    db.close()

    reopened = SecureVectorDB.open(db_path)
    health = reopened.persistence_health()

    assert len(reopened.store) == 0
    assert reopened.verify_dataset() is True
    assert health["status"] == "healthy"
    assert health["record_count"] == 0
    assert health["learned_index"]["status"] == "disabled"

    reopened.close()


def test_replacement_survives_reopen_without_duplicates(tmp_path: Path) -> None:
    db_path = tmp_path / "replacement.sqlite"

    db = SecureVectorDB.open(db_path)
    db.insert(7, "version antigua", {"version": 1})
    db.insert(7, "version nueva", {"version": 2})
    root_after_replace = db.root_hash
    db.close()

    reopened = SecureVectorDB.open(db_path)
    record = reopened.search_by_id(7)

    assert record is not None
    assert record.text == "version nueva"
    assert record.metadata["version"] == 2
    assert len(reopened.store) == 1
    assert reopened.root_hash == root_after_replace
    assert reopened.persistence_health()["status"] == "healthy"

    reopened.close()
