from __future__ import annotations

import pytest

from secure_vector_db.crypto.incremental_merkle import (
    IncrementalMerkleTree,
    compute_merkle_root_hex,
    hash_leaf,
    hash_pair,
)


def test_incremental_root_matches_full_rebuild() -> None:
    items = [
        (3, "registro tres"),
        (1, "registro uno"),
        (2, "registro dos"),
    ]

    tree = IncrementalMerkleTree.from_items(items)

    assert tree.root_hex == compute_merkle_root_hex(items)
    assert tree.verify_against_full_rebuild() is True


def test_update_existing_leaf_recomputes_path_only() -> None:
    tree = IncrementalMerkleTree.from_items(
        [
            (1, "uno"),
            (2, "dos"),
            (3, "tres"),
            (4, "cuatro"),
        ]
    )

    result = tree.update_leaf(2, "dos actualizado")

    assert result.mode == "path"
    assert result.touched_nodes > 0
    assert tree.root_hex == compute_merkle_root_hex(
        [
            (1, "uno"),
            (2, "dos actualizado"),
            (3, "tres"),
            (4, "cuatro"),
        ]
    )


def test_update_same_leaf_is_noop() -> None:
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos")])

    result = tree.update_leaf(1, "uno")

    assert result.mode == "noop"
    assert result.touched_nodes == 0
    assert tree.verify_against_full_rebuild() is True


def test_insert_new_leaf_rebuilds_shape() -> None:
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos")])

    result = tree.update_leaf(3, "tres")

    assert result.mode == "rebuild"
    assert tree.size == 3
    assert tree.root_hex == compute_merkle_root_hex([(1, "uno"), (2, "dos"), (3, "tres")])


def test_delete_leaf_rebuilds_shape() -> None:
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos"), (3, "tres")])

    result = tree.delete_leaf(2)

    assert result.mode == "rebuild"
    assert tree.size == 2
    assert tree.contains(2) is False
    assert tree.root_hex == compute_merkle_root_hex([(1, "uno"), (3, "tres")])


def test_delete_missing_leaf_is_noop() -> None:
    tree = IncrementalMerkleTree.from_items([(1, "uno")])

    result = tree.delete_leaf(9)

    assert result.mode == "noop"
    assert tree.size == 1


def test_recompute_path_to_root_returns_touched_nodes() -> None:
    tree = IncrementalMerkleTree.from_items([(1, "uno"), (2, "dos"), (3, "tres")])

    touched = tree.recompute_path_to_root(1)

    assert touched
    assert touched[0].level == 0
    assert touched[-1].digest_hex == tree.root_hex


def test_leaf_digest_hex_rejects_missing_record() -> None:
    tree = IncrementalMerkleTree.from_items([(1, "uno")])

    with pytest.raises(KeyError, match="record_id no existe"):
        tree.leaf_digest_hex(99)


def test_invalid_record_id_is_rejected() -> None:
    tree = IncrementalMerkleTree()

    with pytest.raises(ValueError, match="record_id debe ser"):
        tree.update_leaf(-1, "valor")


def test_hash_helpers_are_domain_separated() -> None:
    leaf = hash_leaf("dato")
    pair = hash_pair(leaf, leaf)

    assert leaf != pair
    assert len(leaf) == 32
    assert len(pair) == 32


def test_empty_tree_has_empty_root() -> None:
    tree = IncrementalMerkleTree()

    assert tree.root_hex == ""
    assert tree.size == 0
    assert tree.verify_against_full_rebuild() is True
