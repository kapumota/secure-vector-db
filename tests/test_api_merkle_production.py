from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from secure_vector_db.api.merkle_evidence import create_merkle_evidence_router
from secure_vector_db.api.merkle_production import install_merkle_evidence_routes, merkle_production_settings, should_enable_merkle_api
from secure_vector_db.crypto.incremental_merkle import IncrementalMerkleTree
from secure_vector_db.crypto.merkle_audit import JsonlMerkleAuditLog
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore


def _allow() -> None:
    return None


def _deny() -> None:
    raise HTTPException(status_code=403, detail="scope insuficiente")


def test_merkle_router_uses_admin_dependency_for_verify(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)
    app = FastAPI()
    app.include_router(create_merkle_evidence_router(store, read_dependency=_allow, admin_dependency=_deny))
    client = TestClient(app)
    assert client.get("/merkle/root").status_code == 200
    assert client.get("/merkle/verify").status_code == 403


def test_merkle_router_writes_audit_log(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    audit_path = tmp_path / "audit" / "merkle.jsonl"
    tree = IncrementalMerkleTree.from_items([(1, "uno")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)
    audit_log = JsonlMerkleAuditLog(audit_path)
    app = FastAPI()
    app.include_router(create_merkle_evidence_router(store=store, audit_log=audit_log))
    response = TestClient(app).get("/merkle/evidence")
    assert response.status_code == 200
    assert audit_log.read_events()[0].action == "evidence"


def test_install_merkle_evidence_routes_registers_router(tmp_path) -> None:
    app = FastAPI()
    installed = install_merkle_evidence_routes(app, tmp_path / "merkle.sqlite", enabled=True)
    assert installed is True
    assert "/merkle/root" in {route.path for route in app.routes}


def test_install_merkle_evidence_routes_can_be_disabled(tmp_path) -> None:
    app = FastAPI()
    installed = install_merkle_evidence_routes(app, tmp_path / "merkle.sqlite", enabled=False)
    assert installed is False


def test_merkle_production_settings_from_env() -> None:
    settings = merkle_production_settings({
        "SECURE_VECTOR_DB_ENABLE_MERKLE_API": "true",
        "SECURE_VECTOR_DB_MERKLE_DB_PATH": "merkle.sqlite",
        "SECURE_VECTOR_DB_MERKLE_AUDIT_LOG": "audit.jsonl",
    })
    assert settings["enabled"] is True
    assert settings["database_path"] == "merkle.sqlite"
    assert settings["audit_log_configured"] is True
    assert should_enable_merkle_api({"SECURE_VECTOR_DB_ENABLE_MERKLE_API": "si"}) is True
