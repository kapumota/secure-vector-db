from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np


class HNSWVectorIndex:
    """Índice HNSW opcional usando hnswlib.

    Es aproximado y pensado para mayor escala que KD-Tree. Requiere `hnswlib`.
    """

    backend_name = "hnsw"

    def __init__(self, dimensions: int, max_elements: int = 10_000, ef: int = 64, m: int = 16):
        if dimensions <= 0:
            raise ValueError("dimensions debe ser positivo")
        try:
            import hnswlib  # type: ignore
        except Exception as exc:  # pragma: no cover - depende del entorno
            raise ImportError("hnswlib no está instalado. Instale `hnswlib` o use vector_index='kd_tree'.") from exc
        self._hnswlib = hnswlib
        self.dimensions = dimensions
        self.max_elements = max_elements
        self.ef = ef
        self.m = m
        self._vectors: dict[int, List[float]] = {}
        self._deleted: set[int] = set()
        self._new_index(max_elements)

    def _new_index(self, max_elements: int) -> None:
        self._index = self._hnswlib.Index(space="l2", dim=self.dimensions)
        self._index.init_index(max_elements=max(max_elements, 1), ef_construction=100, M=self.m)
        self._index.set_ef(self.ef)
        self._capacity = max(max_elements, 1)

    def _ensure_capacity(self, extra: int = 1) -> None:
        needed = len(self._vectors) + extra
        if needed <= self._capacity:
            return
        new_capacity = max(needed, self._capacity * 2)
        self._index.resize_index(new_capacity)
        self._capacity = new_capacity

    def insert(self, record_id: int, vector: Iterable[float]) -> None:
        rid = int(record_id)
        values = [float(x) for x in vector]
        if len(values) != self.dimensions:
            raise ValueError(f"vector debe tener dimension {self.dimensions}")
        if rid in self._vectors and rid not in self._deleted:
            self.delete(rid)
        self._vectors[rid] = values
        self._ensure_capacity()
        self._index.add_items(np.asarray([values], dtype="float32"), np.asarray([rid], dtype="int64"))
        self._deleted.discard(rid)

    def delete(self, record_id: int) -> bool:
        rid = int(record_id)
        existed = self._vectors.pop(rid, None) is not None
        if existed and rid not in self._deleted:
            self._index.mark_deleted(rid)
            self._deleted.add(rid)
        return existed

    def rebuild(self, items: Iterable[Tuple[int, Sequence[float]]]) -> None:
        self._vectors = {int(rid): [float(x) for x in vector] for rid, vector in items}
        self._deleted = set()
        self._new_index(max(self.max_elements, len(self._vectors) or 1))
        if self._vectors:
            self._index.add_items(
                np.asarray(list(self._vectors.values()), dtype="float32"),
                np.asarray(list(self._vectors.keys()), dtype="int64"),
            )

    def knn(self, vector: Iterable[float], k: int = 3) -> List[Tuple[int, float]]:
        if k <= 0 or not self._vectors:
            return []
        query = [float(x) for x in vector]
        if len(query) != self.dimensions:
            raise ValueError(f"query debe tener dimension {self.dimensions}")
        kk = min(k, len(self._vectors))
        labels, distances = self._index.knn_query(np.asarray([query], dtype="float32"), k=kk)
        result = [(int(rid), float(dist) ** 0.5) for rid, dist in zip(labels[0], distances[0])]
        result.sort(key=lambda item: item[1])
        return result

    @property
    def size(self) -> int:
        return len(self._vectors)
