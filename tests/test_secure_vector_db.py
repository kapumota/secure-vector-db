from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from benchmarks.benchmark import compare_backends, run_benchmark, write_csv_report
from secure_vector_db.api.auth import DEFAULT_DEV_API_KEY
from secure_vector_db.api.rate_limit import InMemoryRateLimiter
from secure_vector_db.api.server import app
from secure_vector_db.database import SecureVectorDB
from secure_vector_db.errors import IntegrityError, ValidationError
from secure_vector_db.indexes.bplus_tree import BPlusTree
from secure_vector_db.indexes.factory import create_vector_index
from secure_vector_db.indexes.kd_tree_vector_index import KDTreeVectorIndex
from secure_vector_db.ml.embeddings import HashEmbeddingModel, create_embedding_model, euclidean


def test_insert_find_verify():
    db = SecureVectorDB()
    db.insert(10, "documento de prueba", {"a": 1})
    assert db.search_by_id(10).text == "documento de prueba"
    assert db.verify_dataset()


def test_range_and_semantic():
    db = SecureVectorDB()
    for i, text in [(1, "base datos"), (2, "criptografia merkle"), (3, "machine learning")]:
        db.insert(i, text)
    assert [r.record_id for r in db.search_by_range(1, 2)] == [1, 2]
    assert len(db.semantic_search("merkle integridad", k=2)) == 2


def test_duplicate_id_overwrites_record_cleanly():
    db = SecureVectorDB()
    db.insert(1, "texto inicial")
    db.insert(1, "texto reemplazado")
    assert len(db.store) == 1
    assert db.search_by_id(1).text == "texto reemplazado"
    assert db.verify_dataset()


def test_delete_record_updates_indexes_and_integrity():
    db = SecureVectorDB()
    db.insert(1, "uno")
    db.insert(2, "dos")
    assert db.delete(1) is True
    assert db.search_by_id(1) is None
    assert [r.record_id for r in db.search_by_range(1, 2)] == [2]
    assert db.verify_dataset()
    assert db.delete(99) is False


def test_integrity_detects_tampering():
    db = SecureVectorDB()
    db.insert(1, "texto original")
    assert db.verify_dataset()
    db.tamper_text_for_demo(1, "texto alterado")
    assert not db.verify_dataset()
    with pytest.raises(IntegrityError):
        db.assert_integrity()


def test_empty_dataset_is_valid_and_searches_empty():
    db = SecureVectorDB()
    assert db.root_hash == ""
    assert db.verify_dataset()
    assert db.search_by_id(1) is None
    assert db.search_by_range(1, 5) == []
    assert db.semantic_search("consulta", k=3) == []


def test_invalid_inputs_are_controlled():
    db = SecureVectorDB()
    with pytest.raises(ValidationError):
        db.insert(-1, "x")
    with pytest.raises(ValidationError):
        db.insert(1, "")
    with pytest.raises(ValidationError):
        db.search_by_range(5, 1)
    with pytest.raises(ValidationError):
        db.semantic_search("x", k=0)
    with pytest.raises(ValidationError):
        db.semantic_search("", k=1)


def test_json_snapshot_roundtrip(tmp_path: Path):
    path = tmp_path / "db.json"
    db = SecureVectorDB()
    db.insert(1, "persistencia json", {"topic": "storage"})
    db.save(path)
    loaded = SecureVectorDB.load(path)
    assert loaded.search_by_id(1).text == "persistencia json"
    assert loaded.root_hash == db.root_hash
    assert loaded.verify_dataset()


def test_sqlite_persistence_survives_reopen(tmp_path: Path):
    path = tmp_path / "prod.sqlite"
    db = SecureVectorDB.open(path)
    db.insert(1, "persistencia sqlite real", {"topic": "storage"})
    root = db.root_hash
    db.close()

    reopened = SecureVectorDB.open(path)
    assert reopened.search_by_id(1).text == "persistencia sqlite real"
    assert reopened.root_hash == root
    assert reopened.verify_dataset()
    reopened.close()


def test_sqlite_integrity_tamper_detected_after_reopen(tmp_path: Path):
    path = tmp_path / "tamper.sqlite"
    db = SecureVectorDB.open(path)
    db.insert(1, "texto original")
    db.close()

    conn = sqlite3.connect(path)
    conn.execute("UPDATE records SET text=? WHERE record_id=1", ("texto alterado",))
    conn.commit()
    conn.close()

    reopened = SecureVectorDB.open(path)
    assert not reopened.verify_dataset()
    reopened.close()


def test_bplus_duplicate_value_and_delete():
    tree = BPlusTree[int, str](4)
    tree.insert(2, "a")
    tree.insert(2, "a")
    tree.insert(2, "b")
    assert tree.find(2) == ["a", "b"]
    tree.delete(2)
    assert tree.find(2) is None
    assert tree.validate()


def test_api_documents_auth_and_errors(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SECURE_VECTOR_DB_PATH", str(tmp_path / "api-test.sqlite"))
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEY", raising=False)

    with TestClient(app) as client:
        docs = client.get("/openapi.json")
        assert docs.status_code == 200
        assert "/records" in docs.json()["paths"]

        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["storage"].endswith("api-test.sqlite")

        unauth = client.get("/range", params={"start": 1, "end": 2})
        assert unauth.status_code == 401

        headers = {"X-API-Key": DEFAULT_DEV_API_KEY}
        bad = client.get("/range", params={"start": 10, "end": 1}, headers=headers)
        assert bad.status_code == 400
        assert "detail" in bad.json()

        inserted = client.post(
            "/records",
            json={"record_id": 9001, "text": "api auth insert", "metadata": {"source": "test"}},
            headers=headers,
        )
        assert inserted.status_code == 200
        found = client.get("/records/9001", headers=headers)
        assert found.status_code == 200
        assert found.json()["text"] == "api auth insert"




def test_kd_tree_vector_index_matches_exact_linear_order():
    vectors = {
        1: [0.0, 0.0],
        2: [1.0, 1.0],
        3: [0.2, 0.1],
        4: [5.0, 5.0],
    }
    index = KDTreeVectorIndex(dimensions=2)
    index.rebuild(vectors.items())
    query = [0.0, 0.1]
    expected = sorted(((rid, euclidean(query, vector)) for rid, vector in vectors.items()), key=lambda item: item[1])[:3]
    assert index.knn(query, k=3) == expected


def test_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("client", now=100.0)[0] is True
    assert limiter.allow("client", now=101.0)[0] is True
    allowed, remaining, retry_after = limiter.allow("client", now=102.0)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0
    assert limiter.allow("client", now=161.0)[0] is True


def test_concurrent_inserts_are_thread_safe(tmp_path: Path):
    path = tmp_path / "concurrent.sqlite"
    db = SecureVectorDB.open(path)

    def write_record(i: int) -> None:
        db.insert(i, f"documento concurrente {i}", {"worker": i % 4})

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_record, range(80)))

    assert len(db.store) == 80
    assert db.verify_dataset()
    assert len(db.semantic_search("documento concurrente", k=5)) == 5
    db.close()

    reopened = SecureVectorDB.open(path)
    assert len(reopened.store) == 80
    assert reopened.verify_dataset()
    reopened.close()


def test_insert_updates_indexes_incrementally(monkeypatch):
    db = SecureVectorDB()
    rebuild_calls = 0

    def fail_rebuild():
        nonlocal rebuild_calls
        rebuild_calls += 1
        raise AssertionError("insert no debe reconstruir todos los índices")

    monkeypatch.setattr(db, "_rebuild_indexes", fail_rebuild)
    db.insert(101, "indice incremental", {"phase": 1})

    assert rebuild_calls == 0
    assert db.search_by_id(101).text == "indice incremental"
    assert db.vector_index.size == 1
    assert db.verify_dataset()


def test_delete_updates_indexes_incrementally(monkeypatch):
    db = SecureVectorDB()
    db.insert(201, "documento temporal")

    def fail_rebuild():
        raise AssertionError("delete no debe reconstruir todos los índices")

    monkeypatch.setattr(db, "_rebuild_indexes", fail_rebuild)
    assert db.delete(201) is True
    assert db.search_by_id(201) is None
    assert db.vector_index.size == 0
    assert db.verify_dataset()



def test_vector_index_backend_is_configurable_with_kd_tree():
    db = SecureVectorDB(vector_index="kd_tree")
    assert db.vector_index.backend_name == "kd_tree"
    db.insert(1, "vector backend kd tree")
    assert len(db.semantic_search("vector", k=1)) == 1


def test_vector_index_auto_falls_back_when_optional_ann_is_missing():
    db = SecureVectorDB(vector_index="auto")
    assert db.vector_index.backend_name in {"faiss", "hnsw", "kd_tree"}
    db.insert(1, "auto backend")
    assert db.semantic_search("backend", k=1)[0][0].record_id == 1


def test_invalid_vector_index_backend_is_rejected():
    with pytest.raises(ValueError):
        create_vector_index(8, "unknown")




def test_hash_embedding_model_is_default_and_configurable():
    db = SecureVectorDB(embedding_model="hash", embedding_dim=16)
    assert db.embedder.name == "hash"
    assert db.embedding_dim == 16
    rec = db.insert(1, "busqueda semantica configurable")
    assert len(rec.embedding) == 16
    assert len(db.semantic_search("semantica", k=1)) == 1


def test_embedding_auto_falls_back_to_hash_when_sentence_transformers_missing(monkeypatch):
    def fail_sentence_transformer(model_name: str):
        raise RuntimeError("sentence-transformers no disponible")

    monkeypatch.setattr("secure_vector_db.ml.embeddings.SentenceTransformerEmbeddingModel", fail_sentence_transformer)
    model = create_embedding_model("auto", embedding_dim=12)
    assert isinstance(model, HashEmbeddingModel)
    assert model.dim == 12


def test_invalid_embedding_backend_is_rejected():
    with pytest.raises(ValueError):
        create_embedding_model("unknown_embedding")



def test_phase4_benchmark_runs_small_dataset_in_memory():
    result = run_benchmark(records=12, queries=4, k=2, persistent=False, vector_index="kd_tree")
    assert result["actual_vector_index"] == "kd_tree"
    assert result["insert"]["records_per_second"] > 0
    assert result["semantic_search"]["p95_ms"] >= 0
    assert result["verify_merkle"]["valid"] is True


def test_phase4_compare_backends_reports_results_and_skips_optional_missing():
    result = compare_backends(
        backends=["kd_tree", "faiss", "hnsw"],
        records=10,
        queries=3,
        k=2,
        persistent=False,
        embedding_model="hash",
        embedding_dim=8,
    )
    assert result["benchmark_type"] == "ann_backend_comparison"
    assert len(result["results"]) == 3
    assert any(item.get("actual_vector_index") == "kd_tree" for item in result["results"])
    assert "fastest_semantic_search_p95" in result["summary"]


def test_phase4_csv_report_writer(tmp_path: Path):
    result = compare_backends(
        backends=["kd_tree"],
        records=8,
        queries=2,
        k=1,
        persistent=False,
        embedding_model="hash",
        embedding_dim=8,
    )
    output = tmp_path / "report.csv"
    write_csv_report(result, output)
    text = output.read_text(encoding="utf-8")
    assert "requested_vector_index" in text
    assert "kd_tree" in text
