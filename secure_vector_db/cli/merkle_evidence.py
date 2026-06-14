"""CLI interna para evidencia Merkle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from secure_vector_db.crypto.merkle_evidence import (
    build_merkle_evidence_report,
    export_merkle_evidence_json,
    verify_merkle_evidence,
)
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore


def build_parser() -> argparse.ArgumentParser:
    """Construye parser CLI de evidencia Merkle."""
    parser = argparse.ArgumentParser(description="Gestiona evidencia Merkle verificable.")
    parser.add_argument("--db", required=True, help="Ruta al SQLite de Merkle.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("root", help="Muestra raiz Merkle actual.")
    subparsers.add_parser("verify", help="Verifica integridad Merkle.")
    evidence_parser = subparsers.add_parser("evidence", help="Exporta evidencia Merkle.")
    evidence_parser.add_argument("--output", required=True, help="Ruta del JSON de evidencia.")
    evidence_parser.add_argument("--recover-missing-nodes", action="store_true", help="Reconstruye nodos internos faltantes si es seguro.")
    return parser


def run_merkle_evidence_cli(argv: list[str] | None = None) -> int:
    """Ejecuta CLI de evidencia Merkle."""
    args = build_parser().parse_args(argv)
    store = SQLiteMerkleNodeStore(Path(args.db))
    if args.command == "root":
        print(build_merkle_evidence_report(store).root_hex)
        return 0
    if args.command == "verify":
        report = build_merkle_evidence_report(store)
        print(json.dumps(report.to_dict(), sort_keys=True))
        return 0 if verify_merkle_evidence(store) else 2
    if args.command == "evidence":
        report = export_merkle_evidence_json(store, Path(args.output), bool(args.recover_missing_nodes))
        print(json.dumps(report.to_dict(), sort_keys=True))
        return 0 if report.status in {"valid", "recovered", "empty"} else 2
    raise SystemExit("comando no soportado")


if __name__ == "__main__":
    raise SystemExit(run_merkle_evidence_cli())
