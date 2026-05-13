from __future__ import annotations

from secure_vector_db.indexes.kd_tree_vector_index import KDTreeVectorIndex

SUPPORTED_VECTOR_INDEXES = {"auto", "kd_tree", "faiss", "hnsw"}


def create_vector_index(dimensions: int, backend: str = "kd_tree"):
    name = (backend or "kd_tree").strip().lower().replace("-", "_")
    if name not in SUPPORTED_VECTOR_INDEXES:
        raise ValueError(f"vector_index debe ser uno de: {', '.join(sorted(SUPPORTED_VECTOR_INDEXES))}")

    if name in {"auto", "faiss"}:
        try:
            from secure_vector_db.indexes.faiss_vector_index import FaissVectorIndex

            return FaissVectorIndex(dimensions)
        except ImportError:
            if name == "faiss":
                raise

    if name in {"auto", "hnsw"}:
        try:
            from secure_vector_db.indexes.hnsw_vector_index import HNSWVectorIndex

            return HNSWVectorIndex(dimensions)
        except ImportError:
            if name == "hnsw":
                raise

    return KDTreeVectorIndex(dimensions)
