from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from secure_vector_db.ml.embeddings import euclidean


@dataclass(frozen=True)
class _Point:
    record_id: int
    vector: List[float]


@dataclass
class _Node:
    point: _Point
    axis: int
    left: Optional["_Node"] = None
    right: Optional["_Node"] = None


class KDTreeVectorIndex:
    backend_name = "kd_tree"

    """Exact k-NN vector index based on a KD-Tree.

    This is more advanced than a linear scan because it partitions the vector
    space by dimension and prunes branches during nearest-neighbour search.
    The implementation remains deterministic and dependency-light, which keeps
    the project easy to run in academic demos and CI.

    Notes:
    - Best suited for low/medium dimensional vectors such as the current
      hash-based embeddings.
    - For very high-dimensional production embeddings, an ANN index such as
      HNSW, IVF/FAISS or ScaNN would normally be preferred.
    """

    def __init__(self, dimensions: int):
        if dimensions <= 0:
            raise ValueError("dimensions debe ser positivo")
        self.dimensions = dimensions
        self._points: dict[int, List[float]] = {}
        self._root: Optional[_Node] = None
        self._dirty = False

    def insert(self, record_id: int, vector: Iterable[float]) -> None:
        values = [float(x) for x in vector]
        if len(values) != self.dimensions:
            raise ValueError(f"vector debe tener dimension {self.dimensions}")
        self._points[int(record_id)] = values
        self._dirty = True

    def delete(self, record_id: int) -> bool:
        existed = self._points.pop(int(record_id), None) is not None
        if existed:
            self._dirty = True
        return existed

    def rebuild(self, items: Iterable[Tuple[int, Sequence[float]]]) -> None:
        self._points = {int(rid): [float(x) for x in vector] for rid, vector in items}
        self._root = self._build([_Point(rid, vector) for rid, vector in self._points.items()], depth=0)
        self._dirty = False

    def knn(self, vector: Iterable[float], k: int = 3) -> List[Tuple[int, float]]:
        if k <= 0:
            return []
        query = [float(x) for x in vector]
        if len(query) != self.dimensions:
            raise ValueError(f"query debe tener dimension {self.dimensions}")
        if self._dirty:
            self.rebuild(self._points.items())
        heap: list[Tuple[float, int]] = []  # max-heap via negative distance
        self._search(self._root, query, k, heap)
        result = [(rid, -neg_dist) for neg_dist, rid in heap]
        result.sort(key=lambda item: item[1])
        return result

    @property
    def size(self) -> int:
        return len(self._points)

    def _build(self, points: List[_Point], depth: int) -> Optional[_Node]:
        if not points:
            return None
        axis = depth % self.dimensions
        points.sort(key=lambda p: (p.vector[axis], p.record_id))
        mid = len(points) // 2
        return _Node(
            point=points[mid],
            axis=axis,
            left=self._build(points[:mid], depth + 1),
            right=self._build(points[mid + 1 :], depth + 1),
        )

    def _search(self, node: Optional[_Node], query: List[float], k: int, heap: list[Tuple[float, int]]) -> None:
        if node is None:
            return

        dist = euclidean(query, node.point.vector)
        candidate = (-dist, node.point.record_id)
        if len(heap) < k:
            heapq.heappush(heap, candidate)
        elif dist < -heap[0][0]:
            heapq.heapreplace(heap, candidate)

        axis = node.axis
        delta = query[axis] - node.point.vector[axis]
        first, second = (node.left, node.right) if delta < 0 else (node.right, node.left)
        self._search(first, query, k, heap)

        worst = float("inf") if len(heap) < k else -heap[0][0]
        if abs(delta) <= worst:
            self._search(second, query, k, heap)
