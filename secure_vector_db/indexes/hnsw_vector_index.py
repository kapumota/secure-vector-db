from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np


class HNSWVectorIndex:
    """Indice HNSW opcional con control de capacidad fisica y borrados."""

    backend_name = "hnsw"

    def __init__(self, dimensions: int, max_elements: int = 10_000, ef: int = 64, m: int = 16):
        if dimensions <= 0 or max_elements <= 0:
            raise ValueError("dimensions y max_elements deben ser positivos")
        try:
            import hnswlib  # type: ignore
        except Exception as exc:  # pragma: no cover - depende del entorno
            raise ImportError("hnswlib no esta instalado. Instale `hnswlib` o use vector_index='kd_tree'.") from exc
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
        """Cuenta slots fisicos, incluidos los marcados como borrados."""
        occupied = self._index.get_current_count()
        if occupied + extra <= self._capacity:
            return
        # Los tombstones ocupan slots: reconstruirlos antes de aumentar memoria.
        if self._deleted:
            self.rebuild(self._vectors.items())
            occupied = self._index.get_current_count()
        if occupied + extra > self._capacity:
            capacity = max(occupied + extra, self._capacity * 2)
            self._index.resize_index(capacity)
            self._capacity = capacity

    def insert(self, record_id: int, vector: Iterable[float]) -> None:
        rid = int(record_id)
        values = [float(x) for x in vector]
        if len(values) != self.dimensions:
            raise ValueError(f"vector debe tener dimension {self.dimensions}")
        if rid in self._deleted:
            # La reutilizacion de un ID marcado como borrado no es portable
            # entre versiones de hnswlib: reconstruir el conjunto vivo.
            records = dict(self._vectors)
            records[rid] = values
            self.rebuild(records.items())
            return
        if rid not in self._vectors:
            self._ensure_capacity()
        # Una actualizacion de ID existente no consume un nuevo slot.
        self._index.add_items(np.asarray([values], dtype="float32"), np.asarray([rid], dtype="int64"))
        self._vectors[rid] = values

    def delete(self, record_id: int) -> bool:
        rid = int(record_id)
        if rid not in self._vectors:
            return False
        self._index.mark_deleted(rid)
        del self._vectors[rid]
        self._deleted.add(rid)
        # La eliminacion logica puede degradar las consultas aun antes de
        # llenar la capacidad fisica. Compactar por umbral controlado.
        if len(self._deleted) >= max(32, len(self._vectors) * 2):
            self.rebuild(self._vectors.items())
        return True

    def rebuild(self, items: Iterable[Tuple[int, Sequence[float]]]) -> None:
        records = {int(rid): [float(x) for x in vector] for rid, vector in items}
        if any(len(vector) != self.dimensions for vector in records.values()):
            raise ValueError(f"vector debe tener dimension {self.dimensions}")
        self._new_index(max(self.max_elements, len(records), 1))
        if records:
            self._index.add_items(
                np.asarray(list(records.values()), dtype="float32"),
                np.asarray(list(records.keys()), dtype="int64"),
            )
        self._vectors = records
        self._deleted.clear()

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
