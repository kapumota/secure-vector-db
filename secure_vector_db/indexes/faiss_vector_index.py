from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np


class FaissVectorIndex:
    """Índice vectorial FAISS opcional basado en IndexFlatL2 + IDMap.

    Usa búsqueda L2 exacta acelerada en C++ cuando `faiss-cpu` está instalado.
    Mantiene copia ligera de los vectores para soportar rebuild y reemplazos.
    """

    backend_name = "faiss"

    def __init__(self, dimensions: int):
        if dimensions <= 0:
            raise ValueError("dimensions debe ser positivo")
        try:
            import faiss  # type: ignore
        except Exception as exc:  # pragma: no cover - depende del entorno
            raise ImportError("FAISS no está instalado. Instale `faiss-cpu` o use vector_index='kd_tree'.") from exc
        self._faiss = faiss
        self.dimensions = dimensions
        self._vectors: dict[int, List[float]] = {}
        self._new_index()

    def _new_index(self) -> None:
        base = self._faiss.IndexFlatL2(self.dimensions)
        self._index = self._faiss.IndexIDMap2(base)

    def _as_matrix(self, vectors: list[list[float]]) -> np.ndarray:
        return np.asarray(vectors, dtype="float32")

    def insert(self, record_id: int, vector: Iterable[float]) -> None:
        rid = int(record_id)
        values = [float(x) for x in vector]
        if len(values) != self.dimensions:
            raise ValueError(f"vector debe tener dimension {self.dimensions}")
        if rid in self._vectors:
            self.delete(rid)
        self._vectors[rid] = values
        matrix = self._as_matrix([values])
        ids = np.asarray([rid], dtype="int64")
        self._index.add_with_ids(matrix, ids)

    def delete(self, record_id: int) -> bool:
        rid = int(record_id)
        existed = self._vectors.pop(rid, None) is not None
        if existed:
            ids = np.ascontiguousarray(np.asarray([rid], dtype="int64"))
            # FAISS usa selectores para borrar identificadores de forma tipada.
            selector = self._faiss.IDSelectorBatch(ids.size, self._faiss.swig_ptr(ids))
            self._index.remove_ids(selector)
        return existed

    def rebuild(self, items: Iterable[Tuple[int, Sequence[float]]]) -> None:
        self._vectors = {int(rid): [float(x) for x in vector] for rid, vector in items}
        self._new_index()
        if not self._vectors:
            return
        ids = np.asarray(list(self._vectors.keys()), dtype="int64")
        matrix = self._as_matrix(list(self._vectors.values()))
        self._index.add_with_ids(matrix, ids)

    def knn(self, vector: Iterable[float], k: int = 3) -> List[Tuple[int, float]]:
        if k <= 0 or not self._vectors:
            return []
        query = [float(x) for x in vector]
        if len(query) != self.dimensions:
            raise ValueError(f"query debe tener dimension {self.dimensions}")
        kk = min(k, len(self._vectors))
        distances, ids = self._index.search(self._as_matrix([query]), kk)
        result: list[tuple[int, float]] = []
        for rid, squared_dist in zip(ids[0], distances[0]):
            if int(rid) >= 0:
                result.append((int(rid), float(squared_dist) ** 0.5))
        result.sort(key=lambda item: item[1])
        return result

    @property
    def size(self) -> int:
        return len(self._vectors)
