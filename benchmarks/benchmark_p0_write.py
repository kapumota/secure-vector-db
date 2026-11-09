"""Medicion controlada de una escritura sobre una base precargada.

Los tiempos excluyen construccion inicial, apertura y cierre de la base.
Se debe ejecutar la misma herramienta, Python y configuracion sobre ambas
variantes. Este benchmark no demuestra por si solo equivalencia de seguridad.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path

from secure_vector_db.database import SecureVectorDB, SimpleMerkle
from secure_vector_db.storage.record_store import Record


def build_seed(path: Path, count: int) -> None:
    """Prepara la misma base valida sin incluir la carga en la medicion."""
    db = SecureVectorDB.open(path)
    db.close()
    records = [Record(i, f"texto-{i}", {"grupo": "p0"}, [0.01] * 8)
               for i in range(count)]
    root = SimpleMerkle.root_hex([r.canonical() for r in records])
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT INTO records(record_id, text, metadata_json, embedding_json) "
            "VALUES (?, ?, ?, ?)",
            ((r.record_id, r.text, json.dumps(r.metadata), json.dumps(r.embedding))
             for r in records),
        )
        conn.executemany(
            "INSERT INTO kv_meta(key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            [("root_hash", root), ("root_format_version", "2"),
             ("merkle_pending", "0")],
        )


def run_one(path: Path, count: int, operation: str, sidecar: bool) -> float:
    build_seed(path, count)
    old = os.environ.get("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION")
    os.environ["SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION"] = "1" if sidecar else "0"
    try:
        db = SecureVectorDB.open(path)
        start = time.perf_counter()
        if operation == "replace":
            db.insert(count // 2, "reemplazo-p0")
        elif operation == "insert":
            db.insert(count, "insercion-p0")
        elif operation == "delete":
            assert db.delete(count // 2)
        else:
            raise ValueError("Operacion desconocida")
        elapsed = time.perf_counter() - start
        assert db.verify_dataset(), "Integridad principal no verificada"
        assert db.root_hash == db.compute_root_hash(), "Raices discrepantes"
        if sidecar:
            assert db.verify_merkle_integrity(), "Merkle auxiliar discrepante"
        db.close()
        return elapsed
    finally:
        if old is None:
            os.environ.pop("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", None)
        else:
            os.environ["SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION"] = old


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, nargs="+", default=[100, 1000, 10000])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--operation", choices=("replace", "insert", "delete"), default="replace")
    parser.add_argument("--sidecar", action="store_true")
    args = parser.parse_args()
    if min(args.records) <= 1 or args.repeats < 1:
        parser.error("Se requieren al menos dos registros y una repeticion")
    results = []
    for count in args.records:
        samples = []
        for _ in range(args.repeats):
            with tempfile.TemporaryDirectory(prefix="svdb-p0-") as tmp:
                samples.append(run_one(Path(tmp) / "records.sqlite", count,
                                       args.operation, args.sidecar))
        results.append({"records": count, "seconds": samples,
                        "median_seconds": statistics.median(samples)})
    print(json.dumps({"python": platform.python_version(),
                      "operation": args.operation,
                      "sidecar": args.sidecar,
                      "repeats": args.repeats,
                      "results": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
