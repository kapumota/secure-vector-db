from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest
from secure_vector_db.database import SecureVectorDB, SimpleMerkle
from secure_vector_db.errors import IntegrityError, ValidationError
from secure_vector_db.indexes.factory import create_vector_index
from secure_vector_db.indexes.kd_tree_vector_index import KDTreeVectorIndex
from secure_vector_db.ml.embeddings import HashEmbeddingModel, create_embedding_model, euclidean
from secure_vector_db.storage.record_store import Record, RecordStore


def test_record_store_roundtrip_ordering_and_delete() -> None:
    record_a = Record(
        record_id=2,
        text="documento beta",
        metadata={"tema": "b"},
        embedding=[0.1, 0.2],
    )
    record_b = Record(
        record_id=1,
        text="documento alfa",
        metadata={"tema": "a"},
        embedding=[0.3, 0.4],
    )

    store = RecordStore()
    store.insert(record_a)
    store.insert(record_b)

    serialized = record_a.to_dict()
    restored = Record.from_dict(serialized)

    assert restored.record_id == 2
    assert "documento beta" in restored.canonical()
    assert [record.record_id for record in store.all()] == [1, 2]
    assert store.get(999) is None
    assert store.delete(2) is True
    assert store.delete(2) is False
    assert len(store.to_list()) == 1


def test_kd_tree_validation_rebuild_delete_and_knn() -> None:
    with pytest.raises(ValueError, match="positivo"):
        KDTreeVectorIndex(0)

    index = KDTreeVectorIndex(2)

    with pytest.raises(ValueError, match="dimension"):
        index.insert(1, [1.0])

    index.insert(1, [0.0, 0.0])
    index.insert(2, [1.0, 1.0])
    index.insert(3, [0.1, 0.1])

    assert index.size == 3
    assert index.knn([0.0, 0.0], k=0) == []
    assert index.knn([0.0, 0.0], k=2)[0][0] == 1

    with pytest.raises(ValueError, match="dimension"):
        index.knn([1.0], k=1)

    assert index.delete(2) is True
    assert index.delete(2) is False

    index.rebuild([(5, [2.0, 2.0]), (4, [1.0, 1.0])])
    assert [record_id for record_id, _ in index.knn([1.1, 1.1], k=2)] == [4, 5]


def test_vector_factory_and_hash_embedding_edge_cases(monkeypatch: Any) -> None:
    with pytest.raises(ValueError, match="uno de"):
        create_vector_index(2, "desconocido")

    auto_index = create_vector_index(2, "auto")
    assert auto_index.backend_name in {"kd_tree", "faiss", "hnsw"}

    with pytest.raises(ValueError, match="positivo"):
        HashEmbeddingModel(0)

    model = HashEmbeddingModel(4)
    assert model.encode("") == [0.0, 0.0, 0.0, 0.0]
    encoded = model.encode("texto repetible para cobertura")
    assert len(encoded) == 4
    assert pytest.approx(euclidean(encoded, encoded), abs=1e-9) == 0.0

    def fail_sentence_transformer(_: str) -> None:
        raise RuntimeError("dependencia opcional ausente")

    monkeypatch.setattr(
        "secure_vector_db.ml.embeddings.SentenceTransformerEmbeddingModel",
        fail_sentence_transformer,
    )
    fallback = create_embedding_model("auto", embedding_dim=3)
    assert fallback.name == "hash"
    assert len(fallback.encode("texto")) == 3

    with pytest.raises(ValueError, match="no soportado"):
        create_embedding_model("modelo-invalido")


def test_database_validation_snapshot_and_integrity(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="positivo"):
        SecureVectorDB(embedding_dim=0)

    with pytest.raises(ValidationError, match=">= 3"):
        SecureVectorDB(bplus_order=2)

    db = SecureVectorDB(embedding_dim=4)

    with pytest.raises(ValidationError, match="record_id"):
        db.insert(-1, "texto")

    with pytest.raises(ValidationError, match="text"):
        db.insert(1, " ")

    with pytest.raises(ValidationError, match="metadata"):
        db.insert(1, "texto valido", metadata=["no valido"])  # type: ignore[arg-type]

    db.insert(1, "documento alfa", {"tema": "a"})
    db.insert(2, "documento beta", {"tema": "b"})

    assert db.search_by_id(1) is not None
    assert db.search_by_id(999) is None
    assert len(db.search_by_range(1, 2)) == 2
    assert db.semantic_search("documento", k=1)

    with pytest.raises(ValidationError, match="start_id"):
        db.search_by_range(5, 1)

    with pytest.raises(ValidationError, match="query"):
        db.semantic_search(" ")

    with pytest.raises(ValidationError, match="positivo"):
        db.semantic_search("documento", k=0)

    snapshot = tmp_path / "snapshot.json"
    db.save(snapshot)
    loaded = SecureVectorDB.load(snapshot)

    assert loaded.root_hash == db.root_hash
    assert loaded.verify_dataset() is True

    loaded.tamper_text_for_demo(1, "documento manipulado")
    assert loaded.verify_dataset() is False

    with pytest.raises(IntegrityError, match="Merkle"):
        loaded.assert_integrity()

    loaded.close()
    db.close()


def test_durable_open_rebuilds_indexes_and_persists_metadata(tmp_path: Path) -> None:
    path = tmp_path / "records.sqlite"

    db = SecureVectorDB.open(path, embedding_dim=4, vector_index="kd_tree")
    db.insert(10, "documento persistente", {"tema": "sqlite"})
    root_before_close = db.root_hash
    db.close()

    reopened = SecureVectorDB.open(path, embedding_dim=4, vector_index="kd_tree")

    assert reopened.root_hash == root_before_close
    assert reopened.verify_dataset() is True
    assert reopened.search_by_id(10) is not None
    assert reopened.delete(10) is True
    assert reopened.delete(10) is False

    reopened.close()


def test_simple_merkle_empty_single_and_multiple_items() -> None:
    assert SimpleMerkle.root_hex([]) == ""

    one = SimpleMerkle.root_hex(["a"])
    two = SimpleMerkle.root_hex(["a", "b"])
    three = SimpleMerkle.root_hex(["a", "b", "c"])

    assert len(one) == 64
    assert len(two) == 64
    assert len(three) == 64
    assert len({one, two, three}) == 3


def test_cli_package_is_importable_without_private_exports() -> None:
    cli_module = importlib.import_module("secure_vector_db.cli")

    assert cli_module is not None
    assert getattr(cli_module, "__name__", "") == "secure_vector_db.cli"


def test_release_initial_database_snapshot_export(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.sqlite"
    export_path = tmp_path / "demo.json"

    db = SecureVectorDB.open(db_path, embedding_dim=8, vector_index="kd_tree")
    for record_id, text in (
        (1, "documento alfa de cobertura"),
        (2, "documento beta de cobertura"),
        (3, "documento gamma de cobertura"),
        (4, "documento delta de cobertura"),
        (5, "documento epsilon de cobertura"),
    ):
        db.insert(record_id, text, {"origen": "coverage-uplift"})

    db.save(export_path)
    payload = json.loads(export_path.read_text(encoding="utf-8"))

    assert len(db.store) == 5
    assert payload["root_hash"] == db.root_hash
    assert payload["vector_index"] == "kd_tree"
    assert payload["records"][0]["text"] == "documento alfa de cobertura"
    assert db.verify_dataset() is True

    db.close()
