from __future__ import annotations

import argparse

from fastapi.testclient import TestClient

from benchmarks.benchmark_ordered_index import evaluate_policy, run_benchmark
from secure_vector_db.api.auth import DEFAULT_DEV_API_KEY
from secure_vector_db.api.server import app
from secure_vector_db.database import SecureVectorDB


def test_explain_search_by_id_reports_learned_path() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 8):
        db.insert(record_id, f"documento {record_id}")

    db.train_learned_index(max_error=0)
    plan = db.explain_search_by_id(4)

    assert plan["record_id"] == 4
    assert plan["strategy"] == "learned_index"
    assert plan["learned_enabled"] is True
    assert plan["found_in_window"] is True
    assert plan["fallback_used"] is False
    assert plan["latency_ns"] >= 0


def test_explain_search_by_id_reports_fallback_path() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 8):
        db.insert(record_id, f"documento {record_id}")

    db.train_learned_index(max_error=0)
    plan = db.explain_search_by_id(999)

    assert plan["record_id"] == 999
    assert plan["learned_enabled"] is True
    assert plan["found_in_window"] is False
    assert plan["fallback_used"] is True
    assert plan["strategy"] in {"fallback_bplus_tree", "not_found"}


def test_ordered_explain_endpoint(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SECURE_VECTOR_DB_PATH", str(tmp_path / "api-explain.sqlite"))
    monkeypatch.setenv("SECURE_VECTOR_DB_LEARNED_INDEX", "true")
    monkeypatch.setenv("SECURE_VECTOR_DB_LEARNED_MAX_ERROR", "4")
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.get(
            "/indexes/ordered/explain/1",
            headers={"X-API-Key": DEFAULT_DEV_API_KEY},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["record_id"] == 1
        assert "strategy" in payload
        assert "latency_ns" in payload


def test_policy_recommends_disable_when_fallback_is_high() -> None:
    metrics = {
        "fallback_rate": 0.50,
        "learned_latency_p95_ns": 10,
        "bplus_latency_p95_ns": 20,
        "max_error": 1,
        "configured_max_error": 4,
    }

    result = evaluate_policy(metrics, fallback_threshold=0.10, p95_factor=1.10)

    assert result["recommendation"] == "disable"
    assert "fallback" in result["reason"]


def test_ordered_index_benchmark_smoke() -> None:
    args = argparse.Namespace(
        records=100,
        queries=40,
        distribution="uniform",
        max_error=4,
        fallback_threshold=0.20,
        p95_factor=1.50,
        seed=7,
        json=None,
    )

    metrics = run_benchmark(args)

    assert metrics["query_count"] == 40
    assert metrics["trained_keys"] == 100
    assert "bplus_latency_p95_ns" in metrics
    assert "learned_latency_p95_ns" in metrics
    assert metrics["policy"]["recommendation"] in {"enable", "disable"}
