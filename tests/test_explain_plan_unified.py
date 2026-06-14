from __future__ import annotations

from secure_vector_db.database import SecureVectorDB


def test_explain_record_uses_unified_contract_without_training() -> None:
    db = SecureVectorDB()
    db.insert(1, "documento 1")

    plan = db.explain_record(1)

    assert plan["contract_version"] == 1
    assert plan["operation"] == "get"
    assert plan["record_id"] == 1
    assert plan["primary_index"] == "bplus_tree"
    assert plan["fallback"] == "bplus_tree"
    assert plan["fallback_used"] is False
    assert plan["found"] is True
    assert plan["model_status"] in {"needs_retrain", "disabled"}


def test_explain_record_uses_learned_index_after_training() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 21):
        db.insert(record_id, f"documento {record_id}")

    db.train_learned_index(max_error=4)
    plan = db.explain_record(10)

    assert plan["contract_version"] == 1
    assert plan["operation"] == "get"
    assert plan["plan"] == "hybrid_ordered_index_lookup"
    assert plan["primary_index"] == "learned_piecewise_index"
    assert plan["search_window"] is not None
    assert plan["model_status"] == "healthy"
    assert plan["found"] is True


def test_explain_range_uses_bplus_tree_contract() -> None:
    db = SecureVectorDB()

    for record_id in range(1, 11):
        db.insert(record_id, f"documento {record_id}")

    plan = db.explain_range(3, 7)

    assert plan["contract_version"] == 1
    assert plan["operation"] == "range"
    assert plan["range"] == [3, 7]
    assert plan["plan"] == "bplus_tree_range_scan"
    assert plan["primary_index"] == "bplus_tree"
    assert plan["fallback"] is None
    assert plan["fallback_used"] is False
    assert plan["result_count"] == 5


def test_explain_range_rejects_invalid_bounds() -> None:
    db = SecureVectorDB()

    try:
        db.explain_range(10, 2)
    except Exception as exc:
        assert "start_id" in str(exc)
    else:
        raise AssertionError("explain_range debio rechazar un rango invertido")
