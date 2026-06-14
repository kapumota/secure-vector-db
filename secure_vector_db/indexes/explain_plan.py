"""Contrato unificado de explain plan para consultas ordenadas."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def build_record_explain_plan(
    raw_plan: Mapping[str, Any],
    model_health: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Normaliza el explain plan de busqueda por ID."""
    record_id = raw_plan.get("record_id")
    learned_enabled = bool(raw_plan.get("learned_enabled", False))
    fallback_used = bool(raw_plan.get("fallback_used", False))
    found = bool(raw_plan.get("found", False))

    if learned_enabled:
        primary_index = "learned_piecewise_index"
        plan_name = "hybrid_ordered_index_lookup"
    else:
        primary_index = "bplus_tree"
        plan_name = "bplus_tree_lookup"

    if not found:
        plan_name = f"{plan_name}_not_found"

    window_start = raw_plan.get("window_start")
    window_end = raw_plan.get("window_end")
    search_window = None
    if window_start is not None and window_end is not None:
        search_window = [window_start, window_end]

    model_status = "disabled"
    if model_health is not None:
        model_status = str(model_health.get("status", model_status))
    elif learned_enabled:
        model_status = "enabled"

    return {
        "contract_version": 1,
        "operation": "get",
        "record_id": record_id,
        "plan": plan_name,
        "primary_index": primary_index,
        "fallback": "bplus_tree",
        "fallback_used": fallback_used,
        "predicted_position": raw_plan.get("predicted_position"),
        "search_window": search_window,
        "window_size": raw_plan.get("window_size"),
        "model_status": model_status,
        "learned_enabled": learned_enabled,
        "found": found,
        "bplus_found": bool(raw_plan.get("bplus_found", False)),
        "latency_ns": int(raw_plan.get("latency_ns", 0) or 0),
        "reason": _record_reason(learned_enabled, fallback_used, found),
        "raw_strategy": raw_plan.get("strategy"),
    }


def build_range_explain_plan(
    start_id: int,
    end_id: int,
    result_count: int,
    model_health: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Construye explain plan para busqueda por rango."""
    model_status = "unknown"
    if model_health is not None:
        model_status = str(model_health.get("status", model_status))

    return {
        "contract_version": 1,
        "operation": "range",
        "range": [start_id, end_id],
        "plan": "bplus_tree_range_scan",
        "primary_index": "bplus_tree",
        "fallback": None,
        "fallback_used": False,
        "model_status": model_status,
        "learned_enabled": bool(model_health.get("learned_enabled", False)) if model_health else False,
        "result_count": result_count,
        "order": "ascending_record_id",
        "reason": "las consultas por rango usan B+ Tree como indice ordenado exacto",
    }


def _record_reason(learned_enabled: bool, fallback_used: bool, found: bool) -> str:
    # Describe por que se eligio el plan visible.
    if not found:
        return "el registro no fue encontrado por el plan de acceso"
    if not learned_enabled:
        return "el indice aprendido no esta activo y se uso B+ Tree"
    if fallback_used:
        return "el modelo aprendido no resolvio la busqueda y se uso B+ Tree"
    return "el modelo aprendido resolvio la busqueda dentro de la ventana predicha"
