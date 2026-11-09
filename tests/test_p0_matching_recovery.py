"""Pruebas adversariales de la reconciliacion limitada P0-R1.1."""

import sqlite3

import pytest

from secure_vector_db.database import SecureVectorDB
from secure_vector_db.errors import IntegrityError


def _configure(monkeypatch):
    monkeypatch.setenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "true")
    monkeypatch.delenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", raising=False)
    monkeypatch.delenv("SECURE_VECTOR_DB_MERKLE_DB_PATH", raising=False)


def _make_pending(tmp_path, monkeypatch, *, divergent=False):
    _configure(monkeypatch)
    path = tmp_path / "registros.sqlite"
    db = SecureVectorDB.open(path)
    db.insert(1, "primero")
    if divergent:
        def fail_aux(record):
            raise RuntimeError("auxiliar interrumpido")
        monkeypatch.setattr(db, "_apply_merkle_write_insert", fail_aux)
    else:
        def fail_finalize(key, value):
            if key == "merkle_pending" and value == "0":
                raise RuntimeError("confirmacion interrumpida")
            return original(key, value)
        original = db._durable.set_meta
        monkeypatch.setattr(db._durable, "set_meta", fail_finalize)
    with pytest.raises(IntegrityError, match="SQLite se confirmo"):
        db.insert(2, "segundo")
    trusted = db.root_hash
    db.close()
    return path, trusted


def test_matching_pending_requires_approval_and_external_root(tmp_path, monkeypatch):
    path, root = _make_pending(tmp_path, monkeypatch)
    db = SecureVectorDB.open(path)
    assert not db.verify_dataset()
    evidence = tmp_path / "evidencia"
    with pytest.raises(IntegrityError):
        db.recover_pending_merkle(trusted_root_hex=root, evidence_dir=evidence,
                                  operator_id="operador", approved=False)
    with pytest.raises(IntegrityError):
        db.recover_pending_merkle(trusted_root_hex="0" * 64, evidence_dir=evidence,
                                  operator_id="operador", approved=True)
    assert not evidence.exists()
    assert db._durable.get_meta("merkle_pending", "") == "1"
    db.close()


def test_matching_pending_recovers_after_reopen(tmp_path, monkeypatch):
    path, root = _make_pending(tmp_path, monkeypatch)
    db = SecureVectorDB.open(path)
    evidence = tmp_path / "evidencia"
    result = db.recover_pending_merkle(trusted_root_hex=root, evidence_dir=evidence,
                                       operator_id="auditor-local", approved=True)
    assert result["status"] == "RECOVERED_MATCHING_PENDING"
    assert (evidence / "manifest.json").is_file()
    assert (evidence / "principal_antes.sqlite").is_file()
    assert (evidence / "auxiliar_antes.sqlite").is_file()
    assert db.verify_dataset()
    assert db.verify_merkle_integrity()
    with pytest.raises(IntegrityError):
        db.recover_pending_merkle(trusted_root_hex=root,
                                  evidence_dir=tmp_path / "segunda", operator_id="operador", approved=True)
    db.insert(3, "tercero")
    db.close()
    reopened = SecureVectorDB.open(path)
    assert reopened.verify_dataset()
    assert reopened.search_by_id(3) is not None
    reopened.close()


def test_divergent_pending_remains_blocked(tmp_path, monkeypatch):
    path, root = _make_pending(tmp_path, monkeypatch, divergent=True)
    db = SecureVectorDB.open(path)
    evidence = tmp_path / "no-creada"
    with pytest.raises(IntegrityError, match="divergente"):
        db.recover_pending_merkle(trusted_root_hex=root, evidence_dir=evidence,
                                  operator_id="operador", approved=True)
    assert not evidence.exists()
    assert db._durable.get_meta("merkle_pending", "") == "1"
    with pytest.raises(IntegrityError):
        db.insert(3, "rechazado")
    db.close()


def test_primary_offline_tampering_prevents_recovery(tmp_path, monkeypatch):
    path, root = _make_pending(tmp_path, monkeypatch)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE records SET text='alterado' WHERE record_id=1")
    db = SecureVectorDB.open(path)
    with pytest.raises(IntegrityError):
        db.recover_pending_merkle(trusted_root_hex=root,
                                  evidence_dir=tmp_path / "no-creada", operator_id="operador", approved=True)
    assert db._durable.get_meta("merkle_pending", "") == "1"
    db.close()


def test_marker_clear_failure_preserves_pending(tmp_path, monkeypatch):
    path, root = _make_pending(tmp_path, monkeypatch)
    db = SecureVectorDB.open(path)
    def fail_clear(key, value):
        raise RuntimeError("interrupcion durante confirmacion")
    monkeypatch.setattr(db._durable, "set_meta", fail_clear)
    evidence = tmp_path / "evidencia"
    with pytest.raises(RuntimeError, match="interrupcion"):
        db.recover_pending_merkle(trusted_root_hex=root, evidence_dir=evidence,
                                  operator_id="operador", approved=True)
    assert (evidence / "manifest.json").exists()
    assert db._durable.get_meta("merkle_pending", "") == "1"
    assert not db.verify_dataset()
    db.close()


def test_no_evidence_writes_after_pending_clear(tmp_path, monkeypatch):
    """No escribir evidencia tras el commit que habilita escrituras."""
    from secure_vector_db import p0_recovery

    path, root = _make_pending(tmp_path, monkeypatch)
    db = SecureVectorDB.open(path)
    original = p0_recovery._durable_json

    def validate_precommit(target, payload):
        assert db._durable.get_meta("merkle_pending", "0") == "1"
        return original(target, payload)

    monkeypatch.setattr(p0_recovery, "_durable_json", validate_precommit)
    evidence = tmp_path / "evidencia"
    result = db.recover_pending_merkle(
        trusted_root_hex=root, evidence_dir=evidence,
        operator_id="operador", approved=True,
    )
    assert result["status"] == "RECOVERED_MATCHING_PENDING"
    assert (evidence / "decision.json").is_file()
    assert not (evidence / "resultado.json").exists()
    assert db.verify_dataset()
    db.close()
    reopened = SecureVectorDB.open(path)
    assert reopened.verify_dataset()
    reopened.close()


def test_decision_write_failure_preserves_pending(tmp_path, monkeypatch):
    """Una falla de evidencia previa no puede desbloquear la base."""
    from secure_vector_db import p0_recovery

    path, root = _make_pending(tmp_path, monkeypatch)
    db = SecureVectorDB.open(path)
    original = p0_recovery._durable_json

    def fail_decision(target, payload):
        if target.name == "decision.json":
            raise OSError("fallo del registro de decision")
        return original(target, payload)

    monkeypatch.setattr(p0_recovery, "_durable_json", fail_decision)
    with pytest.raises(OSError, match="fallo del registro de decision"):
        db.recover_pending_merkle(
            trusted_root_hex=root, evidence_dir=tmp_path / "evidencia",
            operator_id="operador", approved=True,
        )
    assert db._durable.get_meta("merkle_pending", "0") == "1"
    assert not db.verify_dataset()
    db.close()
    reopened = SecureVectorDB.open(path)
    assert not reopened.verify_dataset()
    assert reopened.persistence_health()["status"] == "needs_recovery"
    reopened.close()
