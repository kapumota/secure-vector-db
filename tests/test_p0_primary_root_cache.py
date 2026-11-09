"""Regresiones de la raiz Merkle principal tras escrituras reales."""

import pytest

from secure_vector_db.database import SecureVectorDB
from secure_vector_db.errors import IntegrityError


def _check_roots(db):
    # Recomputacion independiente contra los registros actuales.
    assert db.root_hash == db.compute_root_hash()
    assert db.root_hash == db._primary_merkle.root_hex
    assert db.verify_dataset()


@pytest.mark.parametrize("durable", [False, True])
def test_insert_replace_delete_preserves_main_root(tmp_path, durable):
    kwargs = {"storage_path": tmp_path / "records.sqlite"} if durable else {}
    db = SecureVectorDB(**kwargs)
    for record_id in (9, 2, 5, 1, 20, 10):
        db.insert(record_id, f"texto-{record_id}")
        _check_roots(db)
    for record_id in (2, 9, 1):
        db.insert(record_id, f"reemplazo-{record_id}", {"nested": {"x": [1, 2]}})
        _check_roots(db)
    for record_id in (10, 1, 5, 2, 9, 20):
        assert db.delete(record_id)
        _check_roots(db)
    db.close()
    if durable:
        reopened = SecureVectorDB.open(tmp_path / "records.sqlite")
        _check_roots(reopened)
        reopened.close()


def test_write_does_not_recompute_after_prewrite_verification(monkeypatch, tmp_path):
    db = SecureVectorDB.open(tmp_path / "records.sqlite")
    db.insert(1, "primero")
    original = db.compute_root_hash
    calls = []

    def counted():
        calls.append(1)
        return original()

    monkeypatch.setattr(db, "compute_root_hash", counted)
    db.insert(2, "segundo")
    assert len(calls) == 1  # verificacion previa, no segunda recomputacion
    calls.clear()
    db.insert(1, "reemplazado")
    assert len(calls) == 1
    calls.clear()
    db.delete(2)
    assert len(calls) == 1
    db.close()


def test_prewrite_detects_mutation_even_with_cache(tmp_path):
    db = SecureVectorDB.open(tmp_path / "records.sqlite")
    db.insert(1, "original")
    db.tamper_text_for_demo(1, "alterado")
    with pytest.raises(IntegrityError):
        db.insert(2, "rechazado")
    assert db._durable.get_meta("root_hash", "") == db.root_hash
    db.close()


def test_sqlite_failure_restores_cache_and_root(tmp_path, monkeypatch):
    db = SecureVectorDB.open(tmp_path / "records.sqlite")
    db.insert(1, "original")
    before = db.root_hash

    def fail_commit(**kwargs):
        raise RuntimeError("fallo simulado antes de confirmar SQLite")

    monkeypatch.setattr(db._durable, "commit_record_and_root", fail_commit)
    with pytest.raises(RuntimeError, match="fallo simulado"):
        db.insert(2, "no confirmado")
    assert db.root_hash == before
    assert db._primary_merkle.root_hex == before
    assert db.store.get(2) is None
    assert db.verify_dataset()
    db.close()


def test_json_load_rebuilds_cache(tmp_path):
    db = SecureVectorDB()
    db.insert(1, "uno")
    snapshot = tmp_path / "snapshot.json"
    db.save(snapshot)
    restored = SecureVectorDB.load(snapshot)
    _check_roots(restored)
    restored.insert(2, "dos")
    _check_roots(restored)


def test_offline_sqlite_tampering_rejected_on_reopen(tmp_path):
    import sqlite3

    path = tmp_path / "offline.sqlite"
    db = SecureVectorDB.open(path)
    db.insert(1, "original")
    db.close()
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE records SET text='alterado' WHERE record_id=1")
    reopened = SecureVectorDB.open(path)
    assert not reopened.verify_dataset()
    with pytest.raises(IntegrityError):
        reopened.insert(2, "rechazado")
    reopened.close()


def test_real_sqlite_failure_restores_primary_cache(tmp_path):
    from secure_vector_db.errors import StorageError

    db = SecureVectorDB.open(tmp_path / "trigger.sqlite")
    db.insert(1, "estable")
    old_root = db.root_hash
    db._durable.conn.execute(
        "CREATE TRIGGER reject_p0 BEFORE INSERT ON records "
        "WHEN NEW.record_id=2 BEGIN SELECT RAISE(ABORT, 'rechazo'); END"
    )
    with pytest.raises(StorageError):
        db.insert(2, "rechazado")
    assert db.root_hash == old_root
    assert db._primary_merkle.root_hex == old_root
    assert db.store.get(2) is None
    assert db.verify_dataset()
    db.close()


def test_sidecar_failure_preserves_pending_and_blocks_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "1")
    path = tmp_path / "sidecar.sqlite"
    db = SecureVectorDB.open(path)
    db.insert(1, "confirmado")
    _check_roots(db)
    assert db.verify_merkle_integrity()

    def fail_auxiliary(record):
        raise RuntimeError("fallo auxiliar simulado")

    monkeypatch.setattr(db, "_apply_merkle_write_insert", fail_auxiliary)
    with pytest.raises(IntegrityError, match="SQLite se confirmo"):
        db.insert(2, "pendiente")
    assert db._durable.get_meta("merkle_pending", "") == "1"
    assert db._primary_merkle.root_hex == db.root_hash
    assert not db.verify_dataset()
    with pytest.raises(IntegrityError):
        db.insert(3, "rechazado")
    db.close()

    reopened = SecureVectorDB.open(path)
    assert not reopened.verify_dataset()
    assert reopened.persistence_health()["status"] == "needs_recovery"
    reopened.close()


def test_main_root_matches_full_rebuild_on_randomized_workload(tmp_path):
    from random import Random

    rng = Random(20261108)
    db = SecureVectorDB.open(tmp_path / "random.sqlite")
    for _ in range(150):
        record_id = rng.randrange(0, 70)
        if rng.random() < 0.35:
            db.delete(record_id)
        else:
            db.insert(record_id, f"texto-{rng.randrange(100000)}")
        _check_roots(db)
    db.close()
