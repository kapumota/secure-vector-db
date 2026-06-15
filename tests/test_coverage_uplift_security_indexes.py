from __future__ import annotations

from pathlib import Path
import pytest
from fastapi import HTTPException

from secure_vector_db.api.auth import (
    ApiKeyAuthProvider,
    AuthDecision,
    DisabledAuthProvider,
    auth_provider_info,
    build_auth_provider_from_env,
    extract_header,
    parse_api_keys,
)
from secure_vector_db.api.auth_scopes import (
    ADMIN_SCOPE,
    READ_SCOPE,
    WRITE_SCOPE,
    AuthenticatedPrincipal,
    authenticate_with_scope,
    parse_scopes,
    require_auth_scope,
    scope_allows,
    scope_for_endpoint,
)
from secure_vector_db.api.rate_limit import (
    DisabledRateLimiter,
    MemoryRateLimiter,
    RedisRateLimiter,
    build_rate_limiter_from_env,
    rate_limiter_backend_info,
)
from secure_vector_db.crypto.merkle_write_integration import (
    MerkleWriteIntegrator,
    is_merkle_write_integration_enabled,
    merkle_write_audit_log_path,
    merkle_write_database_path,
)
from secure_vector_db.indexes.bplus_tree import BPlusTree
from secure_vector_db.indexes.explain_plan import (
    build_range_explain_plan,
    build_record_explain_plan,
)
from secure_vector_db.indexes.learned_index_health import evaluate_learned_index_health
from secure_vector_db.indexes.learned_piecewise_index import LearnedPiecewiseIndex
from secure_vector_db.storage.record_store import Record


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


def test_bplus_tree_duplicate_values_traverse_and_delete() -> None:
    tree: BPlusTree[int, str] = BPlusTree(order=4)

    for key in [8, 1, 5, 3, 9, 2, 7, 4, 6]:
        tree.insert(key, f"valor-{key}")

    tree.insert(5, "valor-5-extra")
    tree.insert(5, "valor-5-extra")
    tree.delete(99)

    assert tree.find(5) == ["valor-5", "valor-5-extra"]
    assert [key for key, _ in tree.traverse_leaves()] == list(range(1, 10))
    assert tree.validate() is True

    tree.delete(1)
    tree.delete(5)

    assert tree.find(1) is None
    assert tree.find(5) is None
    assert [key for key, _ in tree.traverse_leaves()] == [2, 3, 4, 6, 7, 8, 9]
    assert tree.validate() is True


def test_bplus_tree_rejects_invalid_order_and_repr() -> None:
    with pytest.raises(ValueError):
        BPlusTree(order=2)

    tree: BPlusTree[int, str] = BPlusTree(order=3)
    assert "BPlusTree" in repr(tree)


def test_learned_piecewise_index_non_uniform_windows_and_errors() -> None:
    index = LearnedPiecewiseIndex()
    keys = [1, 2, 4, 8, 16, 32, 64, 128]

    index.train(keys, max_error=2)

    assert index.is_trained is True
    assert index.predict_position(1) == 0
    assert index.predict_position(999) == len(keys) - 1

    start, end = index.search_window(16)
    assert 0 <= start <= end < len(keys)

    stats = index.stats()
    assert stats["entrenado"] is True
    assert stats["claves_entrenadas"] == len(keys)
    assert stats["ventana_busqueda"] >= 2


def test_learned_piecewise_index_validation_paths() -> None:
    index = LearnedPiecewiseIndex()

    with pytest.raises(ValueError):
        index.predict_position(1)

    with pytest.raises(ValueError):
        index.train([1, 1, 2], max_error=1)

    with pytest.raises(TypeError):
        index.train([1, "dos", 3], max_error=1)  # type: ignore[list-item]

    with pytest.raises(ValueError):
        index.train([1, 2, 3], max_error=-1)

    index.train([], max_error=1)
    assert index.is_trained is False
    assert index.stats()["segmentos"] == 0


def test_learned_index_health_status_transitions() -> None:
    healthy = evaluate_learned_index_health(
        {
            "learned_enabled": True,
            "learned_persisted": True,
            "learned_trained_keys": 10,
            "learned_fallback_rate": 0.05,
            "learned_max_error": 1,
            "learned_configured_max_error": 2,
        },
        current_key_count=10,
    )
    degraded = evaluate_learned_index_health(
        {
            "learned_enabled": True,
            "learned_trained_keys": 10,
            "learned_fallback_rate": 0.90,
        },
        current_key_count=10,
    )
    retrain = evaluate_learned_index_health(
        {"learned_enabled": False, "learned_disabled_reason": "modelo obsoleto"},
        current_key_count=5,
    )
    disabled = evaluate_learned_index_health({}, current_key_count=0)

    assert healthy["status"] == "healthy"
    assert degraded["status"] == "degraded"
    assert retrain["status"] == "needs_retrain"
    assert disabled["status"] == "disabled"

    with pytest.raises(ValueError):
        evaluate_learned_index_health({}, current_key_count=1, fallback_threshold=2.0)


def test_explain_plan_covers_found_fallback_and_missing() -> None:
    found = build_record_explain_plan(
        {
            "record_id": 7,
            "learned_enabled": True,
            "fallback_used": False,
            "found": True,
            "window_start": 2,
            "window_end": 4,
            "predicted_position": 3,
            "latency_ns": None,
            "strategy": "learned",
        },
        model_health={"status": "healthy"},
    )
    fallback = build_record_explain_plan(
        {"record_id": 9, "learned_enabled": True, "fallback_used": True, "found": True}
    )
    missing = build_record_explain_plan(
        {"record_id": 99, "learned_enabled": False, "found": False}
    )
    range_plan = build_range_explain_plan(
        start_id=1,
        end_id=10,
        result_count=3,
        model_health={"status": "healthy", "learned_enabled": True},
    )

    assert found["plan"] == "hybrid_ordered_index_lookup"
    assert found["search_window"] == [2, 4]
    assert fallback["fallback_used"] is True
    assert missing["plan"].endswith("_not_found")
    assert range_plan["operation"] == "range"
    assert range_plan["learned_enabled"] is True


def test_auth_provider_edge_paths() -> None:
    assert parse_api_keys(" a, , b ") == ["a", "b"]
    assert extract_header({"x-api-key": "clave"}, "X-API-Key") == "clave"

    provider = ApiKeyAuthProvider(["clave"], principal="cliente")
    assert provider.authenticate({"X-API-Key": "clave"}).principal == "cliente"
    assert provider.authenticate({}).allowed is False
    assert provider.authenticate({"X-API-Key": "otra"}).allowed is False

    disabled = DisabledAuthProvider()
    assert disabled.authenticate({}).allowed is True

    info = auth_provider_info(provider)
    assert info["backend"] == "api_key"
    assert "clave" not in str(info)

    assert AuthDecision.allow("p", "demo").allowed is True
    assert AuthDecision.deny("demo").allowed is False

    with pytest.raises(ValueError):
        ApiKeyAuthProvider([])

    with pytest.raises(RuntimeError):
        build_auth_provider_from_env({"SECURE_VECTOR_DB_AUTH_BACKEND": "api_key"})

    assert build_auth_provider_from_env(
        {"SECURE_VECTOR_DB_AUTH_BACKEND": "disabled"}
    ).authenticate({}).allowed is True

    with pytest.raises(ValueError):
        build_auth_provider_from_env({"SECURE_VECTOR_DB_AUTH_BACKEND": "otro"})


def test_auth_scopes_edge_paths() -> None:
    assert parse_scopes("read, write") == frozenset({READ_SCOPE, WRITE_SCOPE})
    assert scope_allows(frozenset({ADMIN_SCOPE}), WRITE_SCOPE) is True
    assert scope_allows(frozenset({READ_SCOPE}), WRITE_SCOPE) is False

    principal = AuthenticatedPrincipal(
        name="cliente",
        provider="api_key",
        scopes=frozenset({READ_SCOPE}),
    )
    assert principal.has_scope(READ_SCOPE) is True

    provider = ApiKeyAuthProvider(["clave"])
    authenticated = authenticate_with_scope(
        headers={"X-API-Key": "clave"},
        required_scope=READ_SCOPE,
        provider=provider,
        scopes=frozenset({READ_SCOPE}),
    )
    assert authenticated.name == "api-key-client"

    with pytest.raises(HTTPException) as invalid_key:
        authenticate_with_scope(
            headers={"X-API-Key": "otra"},
            required_scope=READ_SCOPE,
            provider=provider,
            scopes=frozenset({READ_SCOPE}),
        )
    assert invalid_key.value.status_code == 401

    with pytest.raises(HTTPException) as missing_scope:
        authenticate_with_scope(
            headers={"X-API-Key": "clave"},
            required_scope=WRITE_SCOPE,
            provider=provider,
            scopes=frozenset({READ_SCOPE}),
        )
    assert missing_scope.value.status_code == 403

    with pytest.raises(ValueError):
        parse_scopes("read, unknown")

    with pytest.raises(ValueError):
        require_auth_scope("unknown")

    assert scope_for_endpoint("POST", "/records") == WRITE_SCOPE
    assert scope_for_endpoint("GET", "/desconocido") == READ_SCOPE


def test_rate_limit_backends_and_env_paths() -> None:
    memory = MemoryRateLimiter(max_requests=2, window_seconds=10)
    assert memory.allow("cliente", now=100.0).allowed is True
    assert memory.allow("cliente", now=101.0).allowed is True
    assert memory.allow("cliente", now=102.0).allowed is False
    assert memory.allow("", now=120.0).key == "unknown"

    fake = FakeRedis()
    redis = RedisRateLimiter(
        redis_url="redis://example/0",
        max_requests=1,
        window_seconds=60,
        redis_client=fake,
    )
    assert redis.allow("cliente", now=120.0).allowed is True
    assert redis.allow("cliente", now=121.0).allowed is False
    assert fake.expirations

    disabled = DisabledRateLimiter()
    assert disabled.allow("").allowed is True
    assert disabled.allow("").key == "unknown"

    assert build_rate_limiter_from_env(
        {
            "SECURE_VECTOR_DB_RATE_LIMIT_BACKEND": "memory",
            "SECURE_VECTOR_DB_RATE_LIMIT_MAX_REQUESTS": "1",
            "SECURE_VECTOR_DB_RATE_LIMIT_WINDOW_SECONDS": "1",
        }
    ).name == "memory"
    assert build_rate_limiter_from_env({"SECURE_VECTOR_DB_RATE_LIMIT_BACKEND": "disabled"}).name == "disabled"

    with pytest.raises(ValueError):
        MemoryRateLimiter(max_requests=0)

    with pytest.raises(ValueError):
        build_rate_limiter_from_env({"SECURE_VECTOR_DB_RATE_LIMIT_BACKEND": "otro"})

    info = rate_limiter_backend_info(memory)
    assert info["backend"] == "memory"
    assert info["distributed"] is False


def test_merkle_write_integration_env_and_manual_rebuild(tmp_path: Path) -> None:
    env = {
        "SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION": "true",
        "SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH": str(tmp_path / "merkle.sqlite"),
        "SECURE_VECTOR_DB_MERKLE_WRITE_AUDIT_LOG": str(tmp_path / "audit.jsonl"),
    }

    assert is_merkle_write_integration_enabled(env) is True
    assert merkle_write_database_path(tmp_path / "records.sqlite", env) == tmp_path / "merkle.sqlite"
    assert merkle_write_audit_log_path(env) == tmp_path / "audit.jsonl"

    integrator = MerkleWriteIntegrator(
        database_path=tmp_path / "merkle.sqlite",
        audit_log_path=tmp_path / "audit.jsonl",
    )
    first = Record(
        record_id=1,
        text="documento uno",
        metadata={"fase": "16.1"},
        embedding=[0.1, 0.2],
    )
    second = Record(
        record_id=2,
        text="documento dos",
        metadata={"fase": "16.1"},
        embedding=[0.3, 0.4],
    )

    rebuilt = integrator.rebuild_from_records([first], operation="load")
    inserted = integrator.apply_insert(second)
    deleted = integrator.apply_delete(1)

    assert rebuilt.persisted is True
    assert inserted.root_hex != rebuilt.root_hex
    assert deleted.leaf_count == 1
    assert integrator.verify_integrity() is True
    assert (tmp_path / "audit.jsonl").exists()

    assert is_merkle_write_integration_enabled(
        {"SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION": "false"}
    ) is False
    assert merkle_write_database_path(None, {}) is None
