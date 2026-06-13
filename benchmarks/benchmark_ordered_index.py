#!/usr/bin/env python3
"""Benchmark comparativo para indice ordenado hibrido."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from statistics import mean
from time import perf_counter_ns
from typing import Any, Callable, Dict, List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from secure_vector_db.database import SecureVectorDB  # noqa: E402


LookupFn = Callable[[int], object]


def percentile(values: Sequence[int], ratio: float) -> int:
    """Calcula percentil deterministico sobre una muestra de latencias."""
    if not values:
        return 0
    ordered = sorted(values)
    index = int((len(ordered) - 1) * ratio)
    return ordered[index]


def generate_keys(records: int, distribution: str) -> List[int]:
    """Genera claves ordenadas para distintas distribuciones."""
    if records <= 0:
        raise ValueError("records debe ser mayor que cero")

    if distribution == "uniform":
        return list(range(1, records + 1))

    if distribution == "gapped":
        return [1 + position * 5 for position in range(records)]

    if distribution == "skewed":
        keys = {1 + int((position / records) ** 2 * records * 20) + position for position in range(records)}
        return sorted(keys)

    if distribution == "clustered":
        keys: set[int] = set()
        cluster_size = max(10, int(records**0.5))
        base = 1
        while len(keys) < records:
            for offset in range(cluster_size):
                if len(keys) >= records:
                    break
                keys.add(base + offset)
            base += cluster_size * 10
        return sorted(keys)

    if distribution == "missing-heavy":
        return list(range(1, records + 1))

    raise ValueError("distribucion no soportada")


def generate_queries(keys: Sequence[int], query_count: int, distribution: str, seed: int) -> List[int]:
    """Genera consultas reproducibles con aciertos y fallos."""
    if query_count <= 0:
        raise ValueError("queries debe ser mayor que cero")

    rng = random.Random(seed)
    queries: List[int] = []
    key_list = list(keys)
    max_key = key_list[-1] if key_list else 0
    hit_ratio = 0.30 if distribution == "missing-heavy" else 0.80

    for position in range(query_count):
        if rng.random() <= hit_ratio:
            queries.append(rng.choice(key_list))
        else:
            queries.append(max_key + 1 + position * 7)

    rng.shuffle(queries)
    return queries


def build_database(keys: Sequence[int]) -> SecureVectorDB:
    """Construye una base en memoria para el benchmark."""
    db = SecureVectorDB()
    for key in keys:
        db.insert(key, f"documento {key}", {"grupo": "benchmark"})
    return db


def bplus_lookup(db: SecureVectorDB, record_id: int) -> object:
    """Busca directamente con B+ Tree para medir la linea base."""
    found = db.id_index.find(record_id)
    if not found:
        return None
    return db.store.get(found[0])


def measure_lookup(lookup: LookupFn, queries: Sequence[int]) -> Dict[str, Any]:
    """Mide latencias e identifica aciertos y fallos."""
    latencies: List[int] = []
    hit_count = 0

    for query in queries:
        started_at = perf_counter_ns()
        result = lookup(query)
        latencies.append(perf_counter_ns() - started_at)
        if result is not None:
            hit_count += 1

    return {
        "latency_avg_ns": int(mean(latencies)) if latencies else 0,
        "latency_p95_ns": percentile(latencies, 0.95),
        "hit_count": hit_count,
        "miss_count": len(queries) - hit_count,
    }


def evaluate_policy(metrics: Dict[str, Any], fallback_threshold: float, p95_factor: float) -> Dict[str, str]:
    """Evalua si conviene activar el indice aprendido."""
    if metrics["fallback_rate"] > fallback_threshold:
        return {
            "recommendation": "disable",
            "reason": "fallback alto frente al umbral configurado",
        }

    if metrics["learned_latency_p95_ns"] > metrics["bplus_latency_p95_ns"] * p95_factor:
        return {
            "recommendation": "disable",
            "reason": "latencia p95 aprendida peor que B+ Tree",
        }

    if metrics["max_error"] > metrics["configured_max_error"]:
        return {
            "recommendation": "disable",
            "reason": "error observado mayor que el error configurado",
        }

    return {
        "recommendation": "enable",
        "reason": "latencia y fallback dentro de umbrales",
    }


def run_benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    """Ejecuta el benchmark comparativo completo."""
    keys = generate_keys(args.records, args.distribution)
    queries = generate_queries(keys, args.queries, args.distribution, args.seed)
    db = build_database(keys)

    bplus_result = measure_lookup(lambda record_id: bplus_lookup(db, record_id), queries)

    train_stats = db.train_learned_index(args.max_error)
    learned_before = db.ordered_index_stats()
    learned_result = measure_lookup(db.search_by_id, queries)
    learned_after = db.ordered_index_stats()

    fallback_count = learned_after["learned_fallback_count"] - learned_before["learned_fallback_count"]
    fallback_rate = fallback_count / len(queries) if queries else 0.0

    metrics: Dict[str, Any] = {
        "distribution": args.distribution,
        "records": len(keys),
        "query_count": len(queries),
        "configured_max_error": args.max_error,
        "bplus_latency_avg_ns": bplus_result["latency_avg_ns"],
        "learned_latency_avg_ns": learned_result["latency_avg_ns"],
        "bplus_latency_p95_ns": bplus_result["latency_p95_ns"],
        "learned_latency_p95_ns": learned_result["latency_p95_ns"],
        "fallback_rate": fallback_rate,
        "fallback_count": fallback_count,
        "window_size": learned_after["learned_window_size"],
        "segments": learned_after["learned_segments"],
        "max_error": learned_after["learned_max_error"],
        "avg_error": learned_after["learned_avg_error"],
        "trained_keys": learned_after["learned_trained_keys"],
        "hit_count": learned_result["hit_count"],
        "miss_count": learned_result["miss_count"],
        "train_stats": train_stats,
    }
    metrics["policy"] = evaluate_policy(metrics, args.fallback_threshold, args.p95_factor)
    return metrics


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser del benchmark."""
    parser = argparse.ArgumentParser(description="Benchmark de indice ordenado hibrido")
    parser.add_argument("--records", type=int, default=10000)
    parser.add_argument("--queries", type=int, default=2000)
    parser.add_argument(
        "--distribution",
        choices=["uniform", "gapped", "skewed", "clustered", "missing-heavy"],
        default="uniform",
    )
    parser.add_argument("--max-error", type=int, default=64)
    parser.add_argument("--fallback-threshold", type=float, default=0.10)
    parser.add_argument("--p95-factor", type=float, default=1.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", type=Path, default=None)
    return parser


def main() -> None:
    """Ejecuta el benchmark desde linea de comandos."""
    args = build_parser().parse_args()
    metrics = run_benchmark(args)
    payload = json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(payload + "\n", encoding="utf-8")

    print(payload)


if __name__ == "__main__":
    main()
