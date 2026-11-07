"""Regresiones sobre defectos verificados en la auditoria de mantenimiento."""

from __future__ import annotations

import hashlib
import importlib.util
import sqlite3
import sys
import types

import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from secure_vector_db.api.auth import DEFAULT_DEV_API_KEY
from secure_vector_db.api.auth_scopes import authenticate_with_scope
from secure_vector_db.api.server import app
from secure_vector_db.crypto.merkle_tree import MerkleTree
from secure_vector_db.database import SecureVectorDB, SimpleMerkle
from secure_vector_db.errors import IntegrityError, StorageError
from secure_vector_db.indexes.hnsw_vector_index import HNSWVectorIndex
from secure_vector_db.storage.record_store import Record
from secure_vector_db.storage.sqlite_store import SQLiteRecordStore


class FakeHNSWIndex:
    """Simula la capacidad fisica de hnswlib, incluidos tombstones."""

    def __init__(self, space, dim):
        self.dim = dim
        self.items = {}
        self.deleted = set()

    def init_index(self, max_elements, ef_construction, M):
        self.capacity = max_elements

    def set_ef(self, ef):
        self.ef = ef

    def get_current_count(self):
        return len(self.items)

    def resize_index(self, new_size):
        self.capacity = new_size

    def add_items(self, vectors, ids):
        for vector, rid in zip(vectors, ids):
            rid = int(rid)
            if rid not in self.items and len(self.items) >= self.capacity:
                raise RuntimeError("limite fisico alcanzado")
            if rid in self.deleted:
                raise RuntimeError("ID eliminado sin reemplazo permitido")
            self.items[rid] = list(vector)

    def mark_deleted(self, rid):
        if rid not in self.items or rid in self.deleted:
            raise RuntimeError("ID inexistente")
        self.deleted.add(rid)

    def knn_query(self, vectors, k):
        query = vectors[0]
        eligible = [
            (rid, sum((float(a) - float(b)) ** 2 for a, b in zip(vector, query)))
            for rid, vector in self.items.items()
            if rid not in self.deleted
        ]
        eligible.sort(key=lambda item: (item[1], item[0]))
        return (
            np.asarray([[item[0] for item in eligible[:k]]]),
            np.asarray([[item[1] for item in eligible[:k]]]),
        )


def test_hnsw_rotation_and_id_reuse(monkeypatch):
    monkeypatch.setitem(sys.modules, "hnswlib", types.SimpleNamespace(Index=FakeHNSWIndex))
    index = HNSWVectorIndex(2, max_elements=5)
    index.insert(0, [0.0, 1.0])
    for rid in range(1, 25):
        index.insert(rid, [float(rid), 0.0])
        assert index.delete(rid - 1) is True
        assert index.size == 1
    assert index.knn([24.0, 0.0], 1)[0][0] == 24
    assert index.delete(24)
    index.insert(24, [1.0, 1.0])
    index.insert(24, [2.0, 2.0])
    assert index.size == 1
    assert index.knn([2.0, 2.0], 1)[0][0] == 24


@pytest.mark.skipif(importlib.util.find_spec("hnswlib") is None, reason="hnswlib opcional")
def test_hnsw_real_rotation_and_deletions():
    index = HNSWVectorIndex(2, max_elements=5)
    index.insert(0, [0.0, 0.0])
    for rid in range(1, 30):
        index.insert(rid, [float(rid), 0.0])
        index.delete(rid - 1)
    assert index.size == 1
    assert index.knn([29.0, 0.0], 1)[0][0] == 29


def test_nested_json_canonicalization_and_precision(tmp_path):
    path = tmp_path / "metadata.sqlite"
    db = SecureVectorDB.open(path)
    first = db.insert(1, "documento", {"cfg": {"z": 1, "a": 2}, 4: [1, 2]})
    assert "svdb-record-v2" in first.canonical()
    assert first.metadata["4"] == [1, 2]
    root = db.root_hash
    db.close()
    reopened = SecureVectorDB.open(path)
    assert reopened.verify_dataset()
    assert reopened.root_hash == root
    assert reopened.search_by_id(1).metadata["cfg"] == {"a": 2, "z": 1}
    reopened.close()
    a = Record(1, "texto", {}, [0.12345671])
    b = Record(1, "texto", {}, [0.12345672])
    assert a.canonical() != b.canonical()
    assert Record(1, "x", {"cfg": {"a": 1, "z": 2}}, []).canonical() == Record(
        1, "x", {"cfg": {"z": 2, "a": 1}}, []
    ).canonical()


def test_verified_legacy_root_migration(tmp_path):
    path = tmp_path / "legacy.sqlite"
    store = SQLiteRecordStore(path)
    record = Record(7, "original", {"x": 1}, [0.25, 0.5])
    store.upsert(record)
    store.set_meta("root_hash", SimpleMerkle.root_hex_legacy([record.canonical_legacy()]))
    store.close()
    db = SecureVectorDB.open(path, embedding_dim=2)
    assert db.verify_dataset() is True
    assert db._durable.get_meta("root_format_version") == "2"
    assert db.root_hash != SimpleMerkle.root_hex_legacy([record.canonical_legacy()])
    db.close()


def test_invalid_legacy_root_is_not_repaired(tmp_path):
    path = tmp_path / "legacy-danada.sqlite"
    store = SQLiteRecordStore(path)
    record = Record(1, "original", {"cfg": {"z": 1, "a": 2}}, [0.5])
    store.upsert(record)
    store.set_meta("root_hash", SimpleMerkle.root_hex_legacy([record.canonical_legacy()]))
    store.close()
    db = SecureVectorDB.open(path, embedding_dim=1)
    assert not db.verify_dataset()
    assert db.persistence_health()["status"] == "needs_recovery"
    with pytest.raises(IntegrityError):
        db.insert(2, "otro")
    db.close()


def test_sqlite_record_and_root_are_atomic(tmp_path):
    path = tmp_path / "atomic.sqlite"
    db = SecureVectorDB.open(path)
    db.insert(1, "uno")
    old_root = db.root_hash
    # Un trigger aborta la sentencia: el contexto transaccional debe
    # conservar el registro y la raiz anteriores.
    with db._durable.conn:
        db._durable.conn.execute(
            "CREATE TRIGGER impedir_insert BEFORE INSERT ON records "
            "WHEN NEW.record_id=2 BEGIN SELECT RAISE(FAIL,'fallo simulado'); END"
        )
    with pytest.raises(StorageError):
        db.insert(2, "dos")
    assert db.root_hash == old_root
    assert db.search_by_id(2) is None
    assert db.verify_dataset()
    db.close()
    reopened = SecureVectorDB.open(path)
    assert reopened.verify_dataset()
    assert reopened.search_by_id(2) is None
    reopened.close()


def test_offline_tampering_does_not_rebuild_merkle(monkeypatch, tmp_path):
    path = tmp_path / "records.sqlite"
    sidecar = tmp_path / "merkle.sqlite"
    monkeypatch.setenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "true")
    monkeypatch.setenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", str(sidecar))
    db = SecureVectorDB.open(path)
    db.insert(1, "original", {"cfg": {"a": 1}})
    old_merkle = db.merkle_integrity_root_hash
    db.close()

    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE records SET text='manipulado' WHERE record_id=1")
    reopened = SecureVectorDB.open(path)
    assert reopened.merkle_integrity_root_hash == old_merkle
    assert not reopened.verify_dataset()
    assert not reopened.verify_merkle_integrity()
    with pytest.raises(IntegrityError):
        reopened.delete(1)
    reopened.close()


def test_forged_primary_root_cannot_hide_sidecar_mismatch(monkeypatch, tmp_path):
    path = tmp_path / "records.sqlite"
    sidecar = tmp_path / "merkle.sqlite"
    monkeypatch.setenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "true")
    monkeypatch.setenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", str(sidecar))
    db = SecureVectorDB.open(path)
    db.insert(1, "original")
    db.close()
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE records SET text='alterado' WHERE record_id=1")
        row = conn.execute(
            "SELECT record_id, text, metadata_json, embedding_json FROM records WHERE record_id=1"
        ).fetchone()
        import json
        changed = Record(row[0], row[1], json.loads(row[2]), json.loads(row[3]))
        forged = SimpleMerkle.root_hex([changed.canonical()])
        conn.execute("UPDATE kv_meta SET value=? WHERE key='root_hash'", (forged,))
    reopened = SecureVectorDB.open(path)
    assert not reopened.verify_merkle_integrity()
    assert reopened.persistence_health()["status"] == "needs_recovery"
    with pytest.raises(IntegrityError):
        reopened.insert(2, "otro")
    reopened.close()


def test_merkle_failure_marks_pending_operation(monkeypatch, tmp_path):
    path = tmp_path / "records.sqlite"
    sidecar = tmp_path / "merkle.sqlite"
    monkeypatch.setenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "true")
    monkeypatch.setenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", str(sidecar))
    db = SecureVectorDB.open(path)
    db.insert(1, "uno")

    def falla(_record):
        raise OSError("interrupcion simulada")

    monkeypatch.setattr(db._merkle_write_integrity, "apply_insert", falla)
    with pytest.raises(IntegrityError, match="reconciliacion controlada"):
        db.insert(2, "dos")
    assert db._durable.get_meta("merkle_pending") == "1"
    assert not db.verify_dataset()
    db.close()
    reopened = SecureVectorDB.open(path)
    assert reopened.persistence_health()["status"] == "needs_recovery"
    assert not reopened.verify_merkle_integrity()
    with pytest.raises(IntegrityError):
        reopened.insert(3, "tres")
    reopened.close()


def test_merkle_update_persists_only_existing_path(monkeypatch, tmp_path):
    path = tmp_path / "records.sqlite"
    sidecar = tmp_path / "merkle.sqlite"
    monkeypatch.setenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "true")
    monkeypatch.setenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", str(sidecar))
    db = SecureVectorDB.open(path)
    for rid in range(1, 6):
        db.insert(rid, f"doc {rid}")

    def no_reescribir(_tree):
        raise AssertionError("Una sustitucion no debe reescribir el arbol entero")

    monkeypatch.setattr(db._merkle_write_integrity.store, "save_tree", no_reescribir)
    db.insert(3, "doc actualizado")
    assert db.verify_merkle_integrity()
    db.close()


def test_scopes_do_not_accept_implicit_dev_key(monkeypatch):
    monkeypatch.setenv("SECURE_VECTOR_DB_API_KEY", "clave-real")
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEYS", raising=False)
    monkeypatch.setenv("SECURE_VECTOR_DB_ALLOW_DEV_API_KEY", "true")
    with pytest.raises(HTTPException) as exc:
        authenticate_with_scope({"X-API-Key": DEFAULT_DEV_API_KEY}, "read")
    assert exc.value.status_code == 401
    principal = authenticate_with_scope({"X-API-Key": "clave-real"}, "read")
    assert principal.has_scope("read")


def test_scopes_without_keys_return_401(monkeypatch):
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEY", raising=False)
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEYS", raising=False)
    monkeypatch.delenv("SECURE_VECTOR_DB_ALLOW_DEV_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        authenticate_with_scope({"X-API-Key": DEFAULT_DEV_API_KEY}, "read")
    assert exc.value.status_code == 401


def test_public_health_hides_internal_paths_and_hashes(tmp_path, monkeypatch):
    monkeypatch.setenv("SECURE_VECTOR_DB_PATH", str(tmp_path / "secreto.sqlite"))
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_legacy_merkle_uses_sha256_and_single_leaf_proof():
    tree = MerkleTree(["unico"])
    assert len(tree.root.value) == hashlib.sha256().digest_size
    assert tree.request_proof("unico") == []
    tree2 = MerkleTree(["uno", "dos"])
    assert len(tree2.request_proof("uno")) == 1

@pytest.mark.skipif(importlib.util.find_spec("faiss") is None, reason="faiss-cpu opcional")
def test_faiss_real_insert_delete_and_replacement():
    from secure_vector_db.indexes.faiss_vector_index import FaissVectorIndex

    index = FaissVectorIndex(2)
    index.insert(1, [0.0, 0.0])
    index.insert(2, [1.0, 1.0])
    assert index.knn([0.0, 0.0], 1)[0][0] == 1
    assert index.delete(1)
    index.insert(1, [4.0, 4.0])
    assert index.knn([4.0, 4.0], 1)[0][0] == 1
    assert index.size == 2


def test_modified_persisted_merkle_node_blocks_writes(monkeypatch, tmp_path):
    path = tmp_path / "records.sqlite"
    sidecar = tmp_path / "merkle.sqlite"
    monkeypatch.setenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "true")
    monkeypatch.setenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", str(sidecar))
    db = SecureVectorDB.open(path)
    db.insert(1, "uno")
    db.insert(2, "dos")
    db.close()
    with sqlite3.connect(sidecar) as conn:
        conn.execute(
            "UPDATE merkle_nodes SET digest_hex=? WHERE level=1",
            ("00" * 32,),
        )
    reopened = SecureVectorDB.open(path)
    assert not reopened.verify_merkle_integrity()
    with pytest.raises(IntegrityError):
        reopened.insert(3, "tres")
    reopened.close()
