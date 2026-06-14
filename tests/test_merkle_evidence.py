from __future__ import annotations

import json

from secure_vector_db.crypto.incremental_merkle import IncrementalMerkleTree, hash_leaf
from secure_vector_db.crypto.merkle_evidence import (
    build_merkle_evidence_report,
    export_merkle_evidence_json,
    verify_merkle_evidence,
)
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore


def test_build_valid_merkle_evidence_report(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)

    report = build_merkle_evidence_report(store)

    assert report.status == "valid"
    assert report.root_hex == tree.root_hex
    assert report.leaf_count == 2
    assert report.node_count > 0
    assert verify_merkle_evidence(store) is True


def test_build_missing_nodes_report(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)
    store.delete_nodes_for_test()

    report = build_merkle_evidence_report(store)

    assert report.status == "missing_nodes"
    assert report.root_hex == tree.root_hex
    assert report.node_count == 0


def test_recover_missing_nodes_from_evidence(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos"), (3, "tres")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)
    store.delete_nodes_for_test()

    report = build_merkle_evidence_report(store, recover_missing_nodes=True)

    assert report.status == "recovered"
    assert report.root_hex == tree.root_hex
    assert report.node_count > 0


def test_build_corrupted_evidence_report(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)
    store.replace_leaf_digest_for_test(1, hash_leaf("corrupto").hex())

    report = build_merkle_evidence_report(store)

    assert report.status == "corrupted"
    assert verify_merkle_evidence(store) is False


def test_export_merkle_evidence_json(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    output_path = tmp_path / "evidence" / "merkle-evidence.json"
    tree = IncrementalMerkleTree.from_items([(1, "uno")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)

    report = export_merkle_evidence_json(store, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert report.status == "valid"
    assert payload["status"] == "valid"
    assert payload["root_hex"] == tree.root_hex


def test_empty_merkle_evidence_report(tmp_path) -> None:
    store = SQLiteMerkleNodeStore(tmp_path / "empty.sqlite")

    report = build_merkle_evidence_report(store)

    assert report.status == "empty"
    assert report.root_hex == ""
    assert report.leaf_count == 0
