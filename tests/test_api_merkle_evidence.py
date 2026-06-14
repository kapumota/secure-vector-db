from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from secure_vector_db.api.merkle_evidence import create_merkle_evidence_router
from secure_vector_db.crypto.incremental_merkle import IncrementalMerkleTree
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore


def test_merkle_evidence_router_reports_root(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)

    app = FastAPI()
    app.include_router(create_merkle_evidence_router(store))
    client = TestClient(app)

    response = client.get("/merkle/root")

    assert response.status_code == 200
    assert response.json()["root_hex"] == tree.root_hex
    assert response.json()["status"] == "valid"


def test_merkle_evidence_router_verifies_integrity(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)

    app = FastAPI()
    app.include_router(create_merkle_evidence_router(store))
    client = TestClient(app)

    response = client.get("/merkle/verify")

    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_merkle_evidence_router_can_recover_missing_nodes(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos"), (3, "tres")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)
    store.delete_nodes_for_test()

    app = FastAPI()
    app.include_router(create_merkle_evidence_router(store))
    client = TestClient(app)

    response = client.get("/merkle/evidence?recover_missing_nodes=true")

    assert response.status_code == 200
    assert response.json()["status"] == "recovered"
    assert response.json()["root_hex"] == tree.root_hex
