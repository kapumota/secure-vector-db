from __future__ import annotations

import json

from secure_vector_db.cli.merkle_evidence import run_merkle_evidence_cli
from secure_vector_db.crypto.incremental_merkle import IncrementalMerkleTree
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore


def test_merkle_evidence_cli_exports_json(tmp_path, capsys) -> None:
    database_path = tmp_path / "merkle.sqlite"
    output_path = tmp_path / "evidence.json"
    tree = IncrementalMerkleTree.from_items([(1, "uno")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)
    exit_code = run_merkle_evidence_cli(["--db", str(database_path), "evidence", "--output", str(output_path)])
    captured = capsys.readouterr()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["status"] == "valid"
    assert "valid" in captured.out


def test_merkle_evidence_cli_verify_returns_error_for_corruption(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno")])
    store = SQLiteMerkleNodeStore(database_path)
    store.save_tree(tree)
    store.replace_leaf_digest_for_test(1, "00" * 32)
    assert run_merkle_evidence_cli(["--db", str(database_path), "verify"]) == 2
