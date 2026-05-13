from __future__ import annotations

import hashlib
import math
from typing import Iterable, List, Protocol


class EmbeddingModel(Protocol):
    """Contrato mínimo para cualquier generador de embeddings."""

    dim: int
    name: str

    def encode(self, text: str) -> List[float]:
        ...


class HashEmbeddingModel:
    """Embedding ligero y determinístico para demo sin dependencias pesadas."""

    name = "hash"

    def __init__(self, dim: int = 8):
        if dim <= 0:
            raise ValueError("dim debe ser positivo")
        self.dim = dim

    def encode(self, text: str) -> List[float]:
        buckets = [0.0] * self.dim
        tokens = text.lower().split()
        if not tokens:
            return buckets
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = digest[0] % self.dim
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            buckets[idx] += sign
        norm = math.sqrt(sum(x * x for x in buckets)) or 1.0
        return [x / norm for x in buckets]


class SentenceTransformerEmbeddingModel:
    """Embeddings semánticos reales usando sentence-transformers.

    La dependencia es opcional. Instalar con:
        pip install -r requirements-embeddings.txt

    Modelo recomendado para demo: sentence-transformers/all-MiniLM-L6-v2.
    Dimensión típica: 384.
    """

    name = "sentence-transformers"

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers no está instalado. "
                "Instala 'pip install -r requirements-embeddings.txt' o usa embedding_model='hash'."
            ) from exc

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        dim = self._model.get_sentence_embedding_dimension()
        if not dim or dim <= 0:
            raise RuntimeError(f"No se pudo determinar la dimensión del modelo {model_name!r}")
        self.dim = int(dim)

    def encode(self, text: str) -> List[float]:
        vector = self._model.encode(text, normalize_embeddings=True)
        return [float(x) for x in vector]


def create_embedding_model(
    embedding_model: str = "hash",
    embedding_dim: int = 8,
    embedding_model_name: str | None = None,
) -> EmbeddingModel:
    """Crea el generador de embeddings configurado.

    - hash: determinístico, rápido, sin dependencias; útil para tests y demo offline.
    - sentence_transformers: embeddings semánticos reales; requiere dependencia opcional.
    - auto: intenta sentence_transformers y cae a hash si no está disponible.
    """
    backend = embedding_model.strip().lower().replace("-", "_")
    if backend == "hash":
        return HashEmbeddingModel(embedding_dim)
    if backend in {"sentence_transformers", "sentence_transformer", "st", "real"}:
        return SentenceTransformerEmbeddingModel(embedding_model_name or "sentence-transformers/all-MiniLM-L6-v2")
    if backend == "auto":
        try:
            return SentenceTransformerEmbeddingModel(embedding_model_name or "sentence-transformers/all-MiniLM-L6-v2")
        except RuntimeError:
            return HashEmbeddingModel(embedding_dim)
    raise ValueError(f"embedding_model no soportado: {embedding_model!r}")


def euclidean(a: Iterable[float], b: Iterable[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
