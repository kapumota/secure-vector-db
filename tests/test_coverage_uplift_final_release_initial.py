from __future__ import annotations

from pathlib import Path

import pytest

from secure_vector_db.crypto.merkle_write_integration import (
    build_merkle_write_integrator_from_env,
    merkle_write_audit_log_path,
    merkle_write_database_path,
)
from secure_vector_db.database import SecureVectorDB
from secure_vector_db.indexes.factory import create_vector_index
from secure_vector_db.indexes.linear_vector_index import LinearVectorIndex
from secure_vector_db.ml.embeddings import HashEmbeddingModel, euclidean
from secure_vector_db.storage.record_store import Record, RecordStore


def test_linear_vector_index_insert_and_knn() -> None:
    index = LinearVectorIndex()

    index.insert(1, [0.0, 0.0, 0.0])
    index.insert(2, [1.0, 0.0, 0.0])
    index.insert(3, [0.0, 1.0, 0.0])

    nearest = index.knn([0.0, 0.0, 0.0], k=2)

    assert nearest[0][0] == 1
    assert len(nearest) == 2
    assert index.knn([0.0, 0.0, 1.0], k=0) == []

def test_record_store_volatile_and_database_persistent_roundtrip(tmp_path: Path) -> None:
    volatile = RecordStore()
    record = Record(
        record_id=42,
        text="documento persistente",
        metadata={"fase": "16.1.5"},
        embedding=[0.1, 0.2, 0.3],
    )

    volatile.insert(record)
    assert volatile.get(42) is not None
    assert volatile.delete(99) is False
    assert volatile.delete(42) is True
    assert volatile.get(42) is None

    persistent_path = tmp_path / "records.sqlite"
    db = SecureVectorDB.open(persistent_path, embedding_dim=3, vector_index="kd_tree")
    db.insert(42, "documento persistente", {"fase": "16.1.5"})
    assert db.search_by_id(42) is not None
    db.close()

    reopened = SecureVectorDB.open(persistent_path, embedding_dim=3, vector_index="kd_tree")
    assert reopened.search_by_id(42) is not None
    assert reopened.delete(42) is True
    assert reopened.search_by_id(42) is None
    reopened.close()


def test_record_store_replace_and_canonical_metadata_ordering() -> None:
    store = RecordStore()
    first = Record(
        record_id=1,
        text="texto uno",
        metadata={"b": 2, "a": 1},
        embedding=[0.1],
    )
    second = Record(
        record_id=1,
        text="texto reemplazado",
        metadata={"a": 1, "b": 2},
        embedding=[0.2],
    )

    store.insert(first)
    store.insert(second)

    assert len(store) == 1
    assert store.get(1).text == "texto reemplazado"  # type: ignore[union-attr]
    canonical = second.canonical()
    assert "(\'a\', 1)" in canonical
    assert "(\'b\', 2)" in canonical


def test_hash_embedding_similarity_and_factory_paths() -> None:
    model = HashEmbeddingModel(6)

    vector_a = model.encode("documento alfa")
    vector_b = model.encode("documento beta")

    assert len(vector_a) == 6
    assert len(vector_b) == 6
    assert sum(value * value for value in vector_a) > 0.0
    assert euclidean(vector_a, vector_a) == pytest.approx(0.0)
    assert euclidean(vector_a, vector_b) >= 0.0

    linear = create_vector_index(6, "kd_tree")
    linear.insert(1, vector_a)
    linear.insert(2, vector_b)

    assert linear.backend_name == "kd_tree"
    assert linear.knn(vector_a, k=1)[0][0] == 1


def test_database_open_variants_and_merkle_env_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", raising=False)
    monkeypatch.delenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", raising=False)
    monkeypatch.delenv("SECURE_VECTOR_DB_MERKLE_WRITE_AUDIT_LOG", raising=False)

    records_path = tmp_path / "records.sqlite"

    db = SecureVectorDB.open(records_path, embedding_dim=6, vector_index="kd_tree")
    db.insert(1, "documento uno", {"fase": "16.1.3"})
    db.insert(2, "documento dos", {"fase": "16.1.3"})

    assert db.merkle_integrity_root_hash == ""
    assert db.verify_merkle_integrity() is True
    assert db.semantic_search("documento", k=2)

    db.close()

    assert merkle_write_database_path(records_path) == records_path.with_suffix(".merkle.sqlite")
    assert merkle_write_database_path(None) is None
    assert merkle_write_audit_log_path() is None
    assert build_merkle_write_integrator_from_env(records_path) is None


def test_database_merkle_write_integrator_from_env_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    merkle_path = tmp_path / "merkle.sqlite"
    audit_path = tmp_path / "audit.jsonl"

    monkeypatch.setenv("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "true")
    monkeypatch.setenv("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH", str(merkle_path))
    monkeypatch.setenv("SECURE_VECTOR_DB_MERKLE_WRITE_AUDIT_LOG", str(audit_path))

    integrator = build_merkle_write_integrator_from_env(tmp_path / "records.sqlite")

    assert integrator is not None
    assert integrator.root_hex == ""
    assert merkle_path.exists()
