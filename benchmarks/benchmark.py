from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from secure_vector_db.database import SecureVectorDB

TOPICS = ["database", "crypto", "search", "ml", "systems", "api"]
WORDS = [
    "vectorial", "merkle", "sqlite", "indice", "busqueda", "integridad",
    "embedding", "hash", "fastapi", "persistencia", "rango", "documento",
    "seguridad", "consulta", "dataset", "latencia", "memoria", "docker",
    "ann", "faiss", "hnsw", "kd-tree", "similaridad", "semantica",
]


def make_text(i: int) -> str:
    random.seed(i)
    return " ".join(random.sample(WORDS, k=8)) + f" registro {i}"


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def sqlite_file_size(path: Path | None) -> int:
    return path.stat().st_size if path and path.exists() else 0


def stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    return {
        "avg_ms": statistics.fmean(values),
        "p50_ms": percentile(values, 50),
        "p95_ms": percentile(values, 95),
        "max_ms": max(values),
    }


def run_benchmark(
    records: int,
    queries: int,
    k: int,
    persistent: bool,
    vector_index: str = "kd_tree",
    embedding_model: str = "hash",
    embedding_dim: int = 8,
    embedding_model_name: str | None = None,
) -> Dict[str, Any]:
    """Ejecuta un benchmark de un backend vectorial.

    Mide inserción, búsqueda por ID, rango, búsqueda vectorial y verificación Merkle.
    Si el backend opcional no está instalado, propaga ImportError para que compare pueda
    marcarlo como skipped sin detener todo el benchmark.
    """
    if records <= 0:
        raise ValueError("records debe ser mayor que 0")
    if queries <= 0:
        raise ValueError("queries debe ser mayor que 0")
    if k <= 0:
        raise ValueError("k debe ser mayor que 0")

    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "benchmark.sqlite" if persistent else None

    tracemalloc.start()
    started_total = time.perf_counter()
    db = SecureVectorDB.open(
        db_path,
        embedding_dim=embedding_dim,
        vector_index=vector_index,
        embedding_model=embedding_model,
        embedding_model_name=embedding_model_name,
    ) if db_path else SecureVectorDB(
        embedding_dim=embedding_dim,
        vector_index=vector_index,
        embedding_model=embedding_model,
        embedding_model_name=embedding_model_name,
    )

    insert_latencies_ms: List[float] = []
    started_insert = time.perf_counter()
    for i in range(records):
        t0 = time.perf_counter()
        db.insert(i, make_text(i), {"topic": TOPICS[i % len(TOPICS)]})
        insert_latencies_ms.append((time.perf_counter() - t0) * 1000)
    insert_total_s = time.perf_counter() - started_insert

    id_latencies_ms: List[float] = []
    range_latencies_ms: List[float] = []
    search_latencies_ms: List[float] = []

    random.seed(42)
    for _ in range(queries):
        rid = random.randrange(0, records)
        t0 = time.perf_counter()
        db.search_by_id(rid)
        id_latencies_ms.append((time.perf_counter() - t0) * 1000)

        start = random.randrange(0, records)
        end = min(records - 1, start + 25)
        t0 = time.perf_counter()
        db.search_by_range(start, end)
        range_latencies_ms.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        db.semantic_search(make_text(rid), k=k)
        search_latencies_ms.append((time.perf_counter() - t0) * 1000)

    verify_started = time.perf_counter()
    valid = db.verify_dataset()
    verify_ms = (time.perf_counter() - verify_started) * 1000

    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total_s = time.perf_counter() - started_total
    size_bytes = sqlite_file_size(db_path)

    actual_backend = db.vector_index.backend_name
    actual_embedding = db.embedder.name
    db.close()
    tmpdir.cleanup()

    return {
        "records": records,
        "queries": queries,
        "k": k,
        "persistent_sqlite": persistent,
        "requested_vector_index": vector_index,
        "actual_vector_index": actual_backend,
        "requested_embedding_model": embedding_model,
        "actual_embedding_model": actual_embedding,
        "embedding_dim": embedding_dim,
        "insert": {
            "total_s": insert_total_s,
            "records_per_second": records / insert_total_s if insert_total_s else 0,
            **stats(insert_latencies_ms),
        },
        "lookup_by_id": stats(id_latencies_ms),
        "range_query_25_ids": stats(range_latencies_ms),
        "semantic_search": stats(search_latencies_ms),
        "verify_merkle": {"valid": valid, "time_ms": verify_ms},
        "memory": {
            "current_mb": current_bytes / (1024 * 1024),
            "peak_mb": peak_bytes / (1024 * 1024),
        },
        "storage": {"sqlite_file_mb": size_bytes / (1024 * 1024)},
        "total_s": total_s,
    }


def compare_backends(
    backends: Iterable[str],
    records: int,
    queries: int,
    k: int,
    persistent: bool,
    embedding_model: str,
    embedding_dim: int,
    embedding_model_name: str | None = None,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for backend in backends:
        try:
            result = run_benchmark(
                records=records,
                queries=queries,
                k=k,
                persistent=persistent,
                vector_index=backend,
                embedding_model=embedding_model,
                embedding_dim=embedding_dim,
                embedding_model_name=embedding_model_name,
            )
            result["status"] = "ok"
        except ImportError as exc:
            result = {
                "requested_vector_index": backend,
                "actual_vector_index": None,
                "status": "skipped",
                "reason": str(exc),
            }
        results.append(result)

    ok = [r for r in results if r.get("status") == "ok"]
    fastest_search = min(ok, key=lambda r: r["semantic_search"]["p95_ms"]) if ok else None
    fastest_insert = max(ok, key=lambda r: r["insert"]["records_per_second"]) if ok else None
    return {
        "benchmark_type": "ann_backend_comparison",
        "records": records,
        "queries": queries,
        "k": k,
        "persistent_sqlite": persistent,
        "embedding_model": embedding_model,
        "embedding_dim": embedding_dim,
        "results": results,
        "summary": {
            "fastest_semantic_search_p95": fastest_search["actual_vector_index"] if fastest_search else None,
            "fastest_insert_throughput": fastest_insert["actual_vector_index"] if fastest_insert else None,
            "skipped": [r["requested_vector_index"] for r in results if r.get("status") == "skipped"],
        },
        "notes": [
            "FAISS y HNSW son dependencias opcionales; si no están instaladas se reportan como skipped.",
            "KD-Tree es exacto y útil como fallback; FAISS/HNSW suelen escalar mejor para más vectores o más dimensiones.",
            "Los resultados dependen del hardware, versión de Python, sistema operativo y carga de la máquina.",
        ],
    }


def write_csv_report(result: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = result.get("results") if result.get("benchmark_type") == "ann_backend_comparison" else [result]
    fieldnames = [
        "status", "requested_vector_index", "actual_vector_index", "records", "queries", "k",
        "records_per_second", "insert_p95_ms", "search_p95_ms", "search_avg_ms",
        "id_p95_ms", "range_p95_ms", "verify_ms", "peak_memory_mb", "total_s", "reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for item in rows:
            writer.writerow({
                "status": item.get("status", "ok"),
                "requested_vector_index": item.get("requested_vector_index"),
                "actual_vector_index": item.get("actual_vector_index"),
                "records": item.get("records"),
                "queries": item.get("queries"),
                "k": item.get("k"),
                "records_per_second": item.get("insert", {}).get("records_per_second"),
                "insert_p95_ms": item.get("insert", {}).get("p95_ms"),
                "search_p95_ms": item.get("semantic_search", {}).get("p95_ms"),
                "search_avg_ms": item.get("semantic_search", {}).get("avg_ms"),
                "id_p95_ms": item.get("lookup_by_id", {}).get("p95_ms"),
                "range_p95_ms": item.get("range_query_25_ids", {}).get("p95_ms"),
                "verify_ms": item.get("verify_merkle", {}).get("time_ms"),
                "peak_memory_mb": item.get("memory", {}).get("peak_mb"),
                "total_s": item.get("total_s"),
                "reason": item.get("reason"),
            })


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark reproducible para SecureVectorDB")
    parser.add_argument("--records", type=int, default=1000, help="Cantidad de registros a insertar")
    parser.add_argument("--queries", type=int, default=100, help="Cantidad de consultas por tipo")
    parser.add_argument("--k", type=int, default=3, help="Vecinos a devolver en búsqueda semántica")
    parser.add_argument("--memory", action="store_true", help="Usar almacenamiento en memoria en vez de SQLite")
    parser.add_argument("--index", default="kd_tree", help="Backend: kd_tree, faiss, hnsw o auto")
    parser.add_argument("--compare", default=None, help="Lista separada por comas. Ej: kd_tree,faiss,hnsw")
    parser.add_argument("--embedding", default="hash", help="Modelo de embedding: hash, sentence_transformers o auto")
    parser.add_argument("--embedding-dim", type=int, default=8, help="Dimensión para embeddings hash")
    parser.add_argument("--embedding-model-name", default=None, help="Nombre del modelo sentence-transformers")
    parser.add_argument("--json", type=Path, default=None, help="Guardar resultados en JSON")
    parser.add_argument("--csv", type=Path, default=None, help="Guardar resumen en CSV")
    args = parser.parse_args()

    if args.compare:
        backends = [x.strip() for x in args.compare.split(",") if x.strip()]
        result = compare_backends(
            backends=backends,
            records=args.records,
            queries=args.queries,
            k=args.k,
            persistent=not args.memory,
            embedding_model=args.embedding,
            embedding_dim=args.embedding_dim,
            embedding_model_name=args.embedding_model_name,
        )
    else:
        result = run_benchmark(
            records=args.records,
            queries=args.queries,
            k=args.k,
            persistent=not args.memory,
            vector_index=args.index,
            embedding_model=args.embedding,
            embedding_dim=args.embedding_dim,
            embedding_model_name=args.embedding_model_name,
        )

    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(output + "\n", encoding="utf-8")
    if args.csv:
        write_csv_report(result, args.csv)


if __name__ == "__main__":
    main()
