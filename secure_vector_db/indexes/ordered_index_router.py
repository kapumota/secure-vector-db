"""Enrutador hibrido con explain plan para indice aprendido y B+ Tree."""

from __future__ import annotations

from time import perf_counter_ns
from typing import Any, Dict, List, Optional, Sequence

from secure_vector_db.indexes.bplus_tree import BPlusTree
from secure_vector_db.indexes.learned_piecewise_index import LearnedPiecewiseIndex


class OrderedIndexRouter:
    """Combina prediccion aprendida, fallback exacto y observabilidad."""

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
            window_result = self._search_learned_window(record_id)
            if window_result is not None:
                return window_result
            self._fallback_count += 1

        return self._find_with_bplus(record_id)

    def explain(self, record_id: int) -> Dict[str, Any]:
        """Devuelve un explain plan de busqueda sin modificar contadores."""
        started_at = perf_counter_ns()
        plan = self._build_explain_plan(record_id)
        plan["latency_ns"] = perf_counter_ns() - started_at
        return plan

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

    def _build_explain_plan(self, record_id: int) -> Dict[str, Any]:
        # Construye el plan sin alterar metricas acumuladas.
        stats = self.stats()
        base_plan: Dict[str, Any] = {
            "record_id": record_id,
            "strategy": "bplus_tree",
            "learned_enabled": self._enabled,
            "predicted_position": None,
            "window_start": None,
            "window_end": None,
            "window_size": stats["learned_window_size"],
            "found_in_window": False,
            "fallback_used": False,
            "segments": stats["learned_segments"],
            "max_error": stats["learned_max_error"],
            "avg_error": stats["learned_avg_error"],
            "found": False,
            "bplus_found": False,
            "latency_ns": 0,
        }

        if not self._enabled:
            found_id = self._find_with_bplus(record_id)
            base_plan["found"] = found_id is not None
            base_plan["bplus_found"] = found_id is not None
            if found_id is None:
                base_plan["strategy"] = "not_found"
            return base_plan

        predicted_position = self._learned_index.predict_position(record_id)
        window_start, window_end = self._learned_index.search_window(record_id)
        found_in_window = self._search_range(record_id, window_start, window_end) is not None

        base_plan.update(
            {
                "predicted_position": predicted_position,
                "window_start": window_start,
                "window_end": window_end,
                "window_size": window_end - window_start + 1,
                "found_in_window": found_in_window,
            }
        )

        if found_in_window:
            base_plan["strategy"] = "learned_index"
            base_plan["found"] = True
            return base_plan

        found_id = self._find_with_bplus(record_id)
        base_plan["fallback_used"] = True
        base_plan["bplus_found"] = found_id is not None
        base_plan["found"] = found_id is not None
        base_plan["strategy"] = "fallback_bplus_tree" if found_id is not None else "not_found"
        return base_plan

    def _search_learned_window(self, record_id: int) -> Optional[int]:
        # Busca en la ventana local predicha por el modelo.
        start, end = self._learned_index.search_window(record_id)
        return self._search_range(record_id, start, end)

    def _search_range(self, record_id: int, start: int, end: int) -> Optional[int]:
        # Busca el ID dentro de una ventana inclusiva.
        for position in range(start, end + 1):
            if self._ordered_keys[position] == record_id:
                return record_id
        return None

    def _find_with_bplus(self, record_id: int) -> Optional[int]:
        # Usa el B+ Tree como fuente exacta de verdad.
        found = self._bplus_tree.find(record_id)
        if not found:
            return None
        return found[0]
