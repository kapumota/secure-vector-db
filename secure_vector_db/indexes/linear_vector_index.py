from __future__ import annotations
from typing import Dict, Iterable, List, Tuple
from secure_vector_db.ml.embeddings import euclidean

class LinearVectorIndex:
    """Índice base usado como referencia exacta para k-NN."""
    def __init__(self):
        self._vectors: Dict[int, List[float]] = {}

    def insert(self, record_id: int, vector: Iterable[float]) -> None:
        self._vectors[record_id] = list(vector)

    def knn(self, vector: Iterable[float], k: int = 3) -> List[Tuple[int, float]]:
        q = list(vector)
        scored = [(rid, euclidean(q, v)) for rid, v in self._vectors.items()]
        scored.sort(key=lambda x: x[1])
        return scored[:k]
