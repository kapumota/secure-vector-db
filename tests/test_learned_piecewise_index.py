from __future__ import annotations

import pytest

from secure_vector_db.database import SecureVectorDB
from secure_vector_db.indexes.bplus_tree import BPlusTree
from secure_vector_db.indexes.learned_piecewise_index import LearnedPiecewiseIndex


def test_uniform_distribution_predicts_exact_positions() -> None:
    keys = list(range(200))
    index = LearnedPiecewiseIndex()

    index.train(keys, max_error=0)

    assert index.stats()["entrenado"] is True
    assert index.stats()["claves_entrenadas"] == 200
    assert index.stats()["segmentos"] == 1
    assert index.stats()["error_maximo_observado"] == 0

    for position, key in enumerate(keys):
        assert index.predict_position(key) == position
        assert index.search_window(key) == (position, position)


def test_gapped_distribution_keeps_windows_inside_bounds() -> None:
    keys = [3, 10, 11, 50, 120, 121, 122, 500, 900]
    index = LearnedPiecewiseIndex()

    index.train(keys, max_error=1)

    for position, key in enumerate(keys):
        predicted = index.predict_position(key)
        start, end = index.search_window(key)

        assert 0 <= predicted < len(keys)
        assert 0 <= start <= end < len(keys)
        assert start <= position <= end


def test_skewed_distribution_respects_configured_error() -> None:
    keys = [value * value for value in range(1, 180)]
    index = LearnedPiecewiseIndex()

    index.train(keys, max_error=4)

    assert index.stats()["error_maximo_observado"] <= 4
    assert index.stats()["segmentos"] > 1

    for position, key in enumerate(keys):
        assert abs(index.predict_position(key) - position) <= 4


def test_predictions_are_clamped_for_external_keys() -> None:
    keys = [10, 20, 30, 100, 200]
    index = LearnedPiecewiseIndex()
    index.train(keys, max_error=1)

    assert index.predict_position(-1000) == 0
    assert index.predict_position(10_000) == len(keys) - 1

    assert index.search_window(-1000)[0] == 0
    assert index.search_window(10_000)[1] == len(keys) - 1


def test_rejects_invalid_training_data() -> None:
    index = LearnedPiecewiseIndex()

    with pytest.raises(ValueError, match="estrictamente ordenadas"):
        index.train([1, 3, 2], max_error=1)

    with pytest.raises(ValueError, match="estrictamente ordenadas"):
        index.train([1, 1, 2], max_error=1)

    with pytest.raises(TypeError, match="enteras"):
        index.train([1, "2", 3], max_error=1)  # type: ignore[list-item]

    with pytest.raises(ValueError, match="negativo"):
        index.train([1, 2, 3], max_error=-1)


def test_untrained_index_rejects_prediction() -> None:
    index = LearnedPiecewiseIndex()

    with pytest.raises(ValueError, match="no esta entrenado"):
        index.predict_position(10)

    with pytest.raises(ValueError, match="no esta entrenado"):
        index.search_window(10)


def test_empty_training_resets_index() -> None:
    index = LearnedPiecewiseIndex()
    index.train([1, 2, 3], max_error=0)
    index.train([], max_error=0)

    assert index.stats()["entrenado"] is False
    assert index.stats()["claves_entrenadas"] == 0
    assert index.stats()["segmentos"] == 0


def test_existing_bplus_and_vector_search_still_work() -> None:
    tree = BPlusTree[int, int](order=4)
    for record_id in (1, 2, 3):
        tree.insert(record_id, record_id)

    assert tree.find(2) == [2]
    assert tree.find(99) is None

    db = SecureVectorDB(vector_index="kd_tree")
    db.insert(1, "base de datos segura", {"tema": "db"})
    db.insert(2, "busqueda vectorial local", {"tema": "vector"})
    db.insert(3, "integridad con arbol merkle", {"tema": "crypto"})

    assert db.search_by_id(2) is not None

    results = db.semantic_search("busqueda local", k=2)
    assert len(results) == 2
