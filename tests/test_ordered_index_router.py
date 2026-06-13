from __future__ import annotations

from secure_vector_db.indexes.bplus_tree import BPlusTree
from secure_vector_db.indexes.ordered_index_router import OrderedIndexRouter


def test_ordered_router_finds_key_with_learned_window() -> None:
    tree = BPlusTree[int, int](order=4)
    keys = [10, 20, 30, 40]
    for key in keys:
        tree.insert(key, key)

    router = OrderedIndexRouter(tree)
    stats = router.train(keys, max_error=0)

    assert stats["learned_enabled"] is True
    assert router.find(30) == 30
    assert router.stats()["learned_fallback_count"] == 0


def test_ordered_router_falls_back_to_bplus_when_window_misses() -> None:
    tree = BPlusTree[int, int](order=4)
    keys = [10, 20, 30, 40]
    for key in keys:
        tree.insert(key, key)

    router = OrderedIndexRouter(tree)
    router.train(keys, max_error=0)

    assert router.find(25) is None

    stats = router.stats()
    assert stats["learned_fallback_count"] == 1
    assert stats["learned_fallback_rate"] > 0.0


def test_ordered_router_can_be_disabled_after_mutation() -> None:
    tree = BPlusTree[int, int](order=4)
    keys = [1, 2, 3]
    for key in keys:
        tree.insert(key, key)

    router = OrderedIndexRouter(tree)
    router.train(keys, max_error=0)
    router.disable("datos modificados despues del entrenamiento")

    assert router.enabled is False
    assert router.find(2) == 2
    assert router.stats()["learned_enabled"] is False
    assert router.stats()["learned_disabled_reason"] == "datos modificados despues del entrenamiento"
