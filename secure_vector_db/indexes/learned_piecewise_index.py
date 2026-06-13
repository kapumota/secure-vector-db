"""Indice aprendido lineal por segmentos para claves ordenadas."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple, Union


StatValue = Union[bool, int, float]


@dataclass(frozen=True)
class LearnedSegment:
    """Representa un segmento lineal entrenado sobre un rango de claves."""

    start_key: int
    end_key: int
    start_position: int
    end_position: int
    slope: float
    intercept: float
    max_error: int
    avg_error: float

    def predict(self, key: int) -> float:
        """Predice la posicion aproximada de una clave dentro del segmento."""
        return self.slope * key + self.intercept


class LearnedPiecewiseIndex:
    """Indice aprendido deterministico para aproximar posiciones ordenadas."""

    def __init__(self) -> None:
        """Inicializa un indice sin entrenamiento."""
        self._keys: List[int] = []
        self._segments: List[LearnedSegment] = []
        self._configured_max_error = 0
        self._observed_max_error = 0
        self._observed_avg_error = 0.0
        self._trained = False

    @property
    def is_trained(self) -> bool:
        """Indica si el indice tiene un modelo entrenado."""
        return self._trained

    @property
    def segments(self) -> Tuple[LearnedSegment, ...]:
        """Devuelve una vista inmutable de los segmentos entrenados."""
        return tuple(self._segments)

    def train(self, keys: Sequence[int], max_error: int) -> None:
        """Entrena segmentos lineales sobre claves enteras estrictamente ordenadas."""
        if max_error < 0:
            raise ValueError("max_error no puede ser negativo.")

        ordered_keys = list(keys)
        self._validate_keys(ordered_keys)

        self._keys = ordered_keys
        self._segments = []
        self._configured_max_error = max_error
        self._observed_max_error = 0
        self._observed_avg_error = 0.0
        self._trained = bool(ordered_keys)

        if not ordered_keys:
            return

        start = 0
        key_count = len(ordered_keys)

        while start < key_count:
            end = start
            best_segment = self._build_segment(ordered_keys, start, end)

            while end + 1 < key_count:
                candidate = self._build_segment(ordered_keys, start, end + 1)
                if candidate.max_error > max_error:
                    break
                end += 1
                best_segment = candidate

            self._segments.append(best_segment)
            start = best_segment.end_position + 1

        self._recompute_observed_errors()

    def predict_position(self, key: int) -> int:
        """Predice una posicion aproximada y siempre la limita al rango valido."""
        self._require_trained()
        segment = self._find_segment(key)
        predicted = int(round(segment.predict(key)))
        return self._clamp_position(predicted)

    def search_window(self, key: int) -> Tuple[int, int]:
        """Devuelve una ventana inclusiva de busqueda alrededor de la prediccion."""
        self._require_trained()
        predicted = self.predict_position(key)
        window = self._window_size()
        return (
            max(0, predicted - window),
            min(len(self._keys) - 1, predicted + window),
        )

    def stats(self) -> Dict[str, StatValue]:
        """Devuelve metricas internas del indice aprendido."""
        return {
            "entrenado": self._trained,
            "claves_entrenadas": len(self._keys),
            "segmentos": len(self._segments),
            "error_maximo_configurado": self._configured_max_error,
            "error_maximo_observado": self._observed_max_error,
            "error_promedio_observado": self._observed_avg_error,
            "ventana_busqueda": self._window_size() if self._trained else 0,
        }

    def _require_trained(self) -> None:
        # Evita predicciones sin modelo entrenado.
        if not self._trained:
            raise ValueError("El indice aprendido no esta entrenado.")

    @staticmethod
    def _validate_keys(keys: Sequence[int]) -> None:
        # Valida claves enteras estrictamente crecientes.
        for position, key in enumerate(keys):
            if not isinstance(key, int):
                raise TypeError("Todas las claves deben ser enteras.")
            if position > 0 and key <= keys[position - 1]:
                raise ValueError("Las claves deben estar estrictamente ordenadas y sin duplicados.")

    @staticmethod
    def _build_segment(keys: Sequence[int], start: int, end: int) -> LearnedSegment:
        # Construye un segmento candidato y mide su error local.
        start_key = keys[start]
        end_key = keys[end]

        if start == end or start_key == end_key:
            slope = 0.0
        else:
            slope = (end - start) / float(end_key - start_key)

        intercept = start - slope * start_key
        errors: List[int] = []

        for position in range(start, end + 1):
            predicted = int(round(slope * keys[position] + intercept))
            errors.append(abs(predicted - position))

        max_error = max(errors) if errors else 0
        avg_error = sum(errors) / len(errors) if errors else 0.0

        return LearnedSegment(
            start_key=start_key,
            end_key=end_key,
            start_position=start,
            end_position=end,
            slope=slope,
            intercept=intercept,
            max_error=max_error,
            avg_error=avg_error,
        )

    def _find_segment(self, key: int) -> LearnedSegment:
        # Ubica el segmento mas cercano para la clave consultada.
        if key <= self._segments[0].end_key:
            return self._segments[0]

        segment_ends = [segment.end_key for segment in self._segments]
        index = bisect_right(segment_ends, key)

        if index >= len(self._segments):
            return self._segments[-1]
        return self._segments[index]

    def _clamp_position(self, position: int) -> int:
        # Limita una posicion al rango de claves entrenadas.
        return max(0, min(len(self._keys) - 1, position))

    def _window_size(self) -> int:
        # Usa una ventana conservadora basada en configuracion y error observado.
        return max(self._configured_max_error, self._observed_max_error)

    def _recompute_observed_errors(self) -> None:
        # Calcula el error observado usando las mismas predicciones publicas.
        errors = [abs(self.predict_position(key) - position) for position, key in enumerate(self._keys)]
        self._observed_max_error = max(errors) if errors else 0
        self._observed_avg_error = sum(errors) / len(errors) if errors else 0.0
