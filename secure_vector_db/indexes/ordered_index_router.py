"""Enrutador hibrido para indice aprendido con fallback exacto a B+ Tree."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from secure_vector_db.indexes.bplus_tree import BPlusTree
from secure_vector_db.indexes.learned_piecewise_index import LearnedPiecewiseIndex


class OrderedIndexRouter:
    """Combina prediccion aprendida con garantia exacta por B+ Tree."""

    def __init__(self, bplus_tree: BPlusTree[int, int]) -> None:
        """Inicializa el enrutador sobre el B+ Tree exacto."""
        self._bplus_tree = bplus_tree
        self._learned_index = LearnedPiecewiseIndex()
        self._ordered_keys: List[int] = []
        self._enabled = False
        self._lookup_count = 0
        self._fallback_count = 0
        self._disabled_reason = "indice aprendido no entrenado"

    @property
    def enabled(self) -> bool:
        """Indica si el camino aprendido esta activo."""
        return self._enabled

    def train(self, keys: Sequence[int], max_error: int) -> Dict[str, Any]:
        """Entrena el indice aprendido con claves ordenadas."""
        ordered_keys = list(keys)
        self._learned_index.train(ordered_keys, max_error)
        self._ordered_keys = ordered_keys
        self._enabled = self._learned_index.is_trained
        self._lookup_count = 0
        self._fallback_count = 0
        self._disabled_reason = "" if self._enabled else "indice aprendido sin claves"
        return self.stats()

    def disable(self, reason: str) -> None:
        """Desactiva el camino aprendido cuando el indice queda obsoleto."""
        self._enabled = False
        self._ordered_keys = []
        self._disabled_reason = reason

    def find(self, record_id: int) -> Optional[int]:
        """Busca un ID usando prediccion aprendida y fallback exacto."""
        self._lookup_count += 1

        if self._enabled:
            start, end = self._learned_index.search_window(record_id)
            for position in range(start, end + 1):
                if self._ordered_keys[position] == record_id:
                    return record_id
            self._fallback_count += 1

        return self._find_with_bplus(record_id)

    def stats(self) -> Dict[str, Any]:
        """Devuelve metricas del indice hibrido."""
        learned_stats = self._learned_index.stats()
        fallback_rate = 0.0
        if self._lookup_count:
            fallback_rate = self._fallback_count / self._lookup_count

        return {
            "learned_enabled": self._enabled,
            "learned_segments": learned_stats["segmentos"],
            "learned_max_error": learned_stats["error_maximo_observado"],
            "learned_avg_error": learned_stats["error_promedio_observado"],
            "learned_fallback_count": self._fallback_count,
            "learned_fallback_rate": fallback_rate,
            "learned_window_size": learned_stats["ventana_busqueda"],
            "learned_lookup_count": self._lookup_count,
            "learned_trained_keys": len(self._ordered_keys),
            "learned_disabled_reason": self._disabled_reason,
        }

    def _find_with_bplus(self, record_id: int) -> Optional[int]:
        # Usa el B+ Tree como fuente exacta de verdad.
        found = self._bplus_tree.find(record_id)
        if not found:
            return None
        return found[0]
