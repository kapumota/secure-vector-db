"""Evaluacion de salud para el indice aprendido."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def evaluate_learned_index_health(
    stats: Mapping[str, Any],
    current_key_count: int,
    fallback_threshold: float = 0.20,
) -> Dict[str, Any]:
    """Evalua salud, degradacion y recomendacion del indice aprendido."""
    if fallback_threshold < 0.0 or fallback_threshold > 1.0:
        raise ValueError("fallback_threshold debe estar entre 0 y 1")

    learned_enabled = bool(stats.get("learned_enabled", False))
    learned_persisted = bool(stats.get("learned_persisted", False))
    trained_key_count = _int(stats.get("learned_trained_keys", 0))
    fallback_rate = _float(stats.get("learned_fallback_rate", 0.0))
    max_observed_error = _int(stats.get("learned_max_error", 0))
    avg_observed_error = _float(stats.get("learned_avg_error", 0.0))
    configured_max_error = _int(stats.get("learned_configured_max_error", max_observed_error))
    disabled_reason = str(stats.get("learned_disabled_reason", ""))

    if learned_enabled:
        inserts_since_training = max(0, current_key_count - trained_key_count)
    else:
        inserts_since_training = current_key_count if current_key_count > 0 else 0

    distribution_changed = current_key_count != trained_key_count
    persisted_model_valid = learned_enabled and not distribution_changed

    status = "healthy"
    recommendation = "keep"
    reason = "indice aprendido activo dentro de umbrales"

    if current_key_count == 0:
        status = "disabled"
        recommendation = "disable"
        reason = "no hay claves para entrenar"
    elif not learned_enabled:
        status = "needs_retrain"
        recommendation = "retrain"
        reason = disabled_reason or "indice aprendido no activo con claves disponibles"
    elif distribution_changed:
        status = "needs_retrain"
        recommendation = "retrain"
        reason = "la cantidad de claves actual no coincide con el entrenamiento"
    elif fallback_rate > fallback_threshold:
        status = "degraded"
        recommendation = "retrain"
        reason = "fallback rate superior al umbral configurado"
    elif max_observed_error > configured_max_error:
        status = "degraded"
        recommendation = "retrain"
        reason = "error observado superior al error configurado"

    return {
        "status": status,
        "recommendation": recommendation,
        "reason": reason,
        "learned_enabled": learned_enabled,
        "learned_persisted": learned_persisted,
        "persisted_model_valid": persisted_model_valid,
        "fallback_rate": fallback_rate,
        "fallback_threshold": fallback_threshold,
        "max_observed_error": max_observed_error,
        "avg_observed_error": avg_observed_error,
        "configured_max_error": configured_max_error,
        "trained_key_count": trained_key_count,
        "current_key_count": current_key_count,
        "inserts_since_training": inserts_since_training,
        "distribution_changed": distribution_changed,
        "needs_retrain": recommendation == "retrain",
    }


def _int(value: Any) -> int:
    # Convierte valores numericos de metricas a entero.
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    # Convierte valores numericos de metricas a flotante.
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
