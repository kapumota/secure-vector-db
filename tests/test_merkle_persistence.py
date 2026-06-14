from __future__ import annotations

import pytest

from secure_vector_db.crypto.incremental_merkle import IncrementalMerkleTree, hash_leaf
from secure_vector_db.crypto.merkle_persistence import (
    MerkleRecoveryError,
    SQLiteMerkleNodeStore,
)


def test_save_and_recover_merkle_tree(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos"), (3, "tres")])
    store = SQLiteMerkleNodeStore(database_path)

    saved = store.save_tree(tree)
    recovered_tree, recovered = SQLiteMerkleNodeStore(database_path).recover_tree()

    assert saved.root_hex == tree.root_hex
    assert recovered_tree.root_hex == tree.root_hex
    assert recovered.leaves == 3
    assert recovered.recovered_from == "nodes"


def test_recovery_from_leaves_when_nodes_are_missing(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos")])
    store = SQLiteMerkleNodeStore(database_path)

    store.save_tree(tree)
    store.delete_nodes_for_test()

    recovered_tree, stats = SQLiteMerkleNodeStore(database_path).recover_tree()

    assert recovered_tree.root_hex == tree.root_hex
    assert stats.recovered_from == "leaves"
    assert stats.nodes == 0


def test_rebuild_missing_nodes_restores_internal_nodes(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos"), (3, "tres")])
    store = SQLiteMerkleNodeStore(database_path)

    store.save_tree(tree)
    store.delete_nodes_for_test()

    rebuilt = store.rebuild_missing_nodes()

    assert rebuilt.root_hex == tree.root_hex
    assert rebuilt.nodes > 0
    assert list(store.iter_node_rows_for_test())


def test_verify_integrity_detects_corrupted_leaf(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos")])
    store = SQLiteMerkleNodeStore(database_path)

    store.save_tree(tree)
    store.replace_leaf_digest_for_test(1, hash_leaf("corrupto").hex())

    assert store.verify_integrity() is False
    with pytest.raises(MerkleRecoveryError, match="raiz Merkle persistida no coincide"):
        store.recover_tree()


def test_empty_tree_can_be_persisted_and_recovered(tmp_path) -> None:
    database_path = tmp_path / "merkle.sqlite"
    tree = IncrementalMerkleTree()
    store = SQLiteMerkleNodeStore(database_path)

    saved = store.save_tree(tree)
    recovered_tree, recovered = SQLiteMerkleNodeStore(database_path).recover_tree()

    assert saved.root_hex == ""
    assert recovered_tree.root_hex == ""
    assert recovered.leaves == 0


def test_from_leaf_digests_restores_incremental_tree() -> None:
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos")])
    restored = IncrementalMerkleTree.from_leaf_digests(tree.snapshot_leaf_digests())

    assert restored.root_hex == tree.root_hex
    assert restored.verify_against_full_rebuild() is True
