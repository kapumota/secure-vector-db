from __future__ import annotations

from pathlib import Path
from typing import Any

from secure_vector_db.crypto.merkle_audit import JsonlMerkleAuditLog
from secure_vector_db.crypto.merkle_evidence import build_merkle_evidence_report
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore
from secure_vector_db.database import SecureVectorDB


def enable_merkle_write(monkeypatch: Any, merkle_path: Path, audit_path: Path) -> None:
    monkeypatch.setenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "true")
    monkeypatch.setenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", str(merkle_path))
    monkeypatch.setenv("SECURE_VECTOR_DB_MERKLE_WRITE_AUDIT_LOG", str(audit_path))


def test_merkle_write_integration_is_disabled_by_default(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.delenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", raising=False)
    monkeypatch.delenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", raising=False)

    db = SecureVectorDB.open(tmp_path / "records.sqlite")
    db.insert(1, "documento alfa", {"topic": "test"})

    assert db.merkle_integrity_root_hash == ""
    assert db.verify_merkle_integrity() is True

    db.close()


def test_insert_and_delete_update_persistent_merkle(tmp_path: Path, monkeypatch: Any) -> None:
    records_path = tmp_path / "records.sqlite"
    merkle_path = tmp_path / "merkle.sqlite"
    audit_path = tmp_path / "merkle-write-audit.jsonl"
    enable_merkle_write(monkeypatch, merkle_path, audit_path)

    db = SecureVectorDB.open(records_path)
    db.insert(1, "documento alfa", {"topic": "a"})
    root_after_first_insert = db.merkle_integrity_root_hash

    db.insert(2, "documento beta", {"topic": "b"})
    root_after_second_insert = db.merkle_integrity_root_hash

    deleted = db.delete(1)
    root_after_delete = db.merkle_integrity_root_hash

    assert deleted is True
    assert root_after_first_insert
    assert root_after_second_insert != root_after_first_insert
    assert root_after_delete != root_after_second_insert
    assert db.verify_merkle_integrity() is True

    store = SQLiteMerkleNodeStore(merkle_path)
    report = build_merkle_evidence_report(store)
    events = JsonlMerkleAuditLog(audit_path).read_events()

    assert report.status == "valid"
    assert report.leaf_count == 1
    assert len(events) >= 3

    db.close()


def test_open_recovers_merkle_from_real_storage(tmp_path: Path, monkeypatch: Any) -> None:
    records_path = tmp_path / "records.sqlite"
    merkle_path = tmp_path / "merkle.sqlite"
    audit_path = tmp_path / "merkle-write-audit.jsonl"
    enable_merkle_write(monkeypatch, merkle_path, audit_path)

    db = SecureVectorDB.open(records_path)
    db.insert(1, "documento alfa", {"topic": "a"})
    db.insert(2, "documento beta", {"topic": "b"})
    root_before_close = db.merkle_integrity_root_hash
    db.close()

    reopened = SecureVectorDB.open(records_path)
    root_after_reopen = reopened.merkle_integrity_root_hash

    assert root_after_reopen == root_before_close
    assert reopened.verify_merkle_integrity() is True

    reopened.close()
