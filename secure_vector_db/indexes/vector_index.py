from __future__ import annotations

from typing import Iterable, List, Protocol, Sequence, Tuple


class VectorIndex(Protocol):
    """Contrato mínimo para índices k-NN usados por SecureVectorDB."""

    def insert(self, record_id: int, vector: Iterable[float]) -> None: ...

    def delete(self, record_id: int) -> bool: ...

    def rebuild(self, items: Iterable[Tuple[int, Sequence[float]]]) -> None: ...

    def knn(self, vector: Iterable[float], k: int = 3) -> List[Tuple[int, float]]: ...

    @property
    def size(self) -> int: ...

    @property
    def backend_name(self) -> str: ...
