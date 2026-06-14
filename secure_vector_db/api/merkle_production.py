"""Instalacion productiva controlada del router Merkle."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from secure_vector_db.api.merkle_evidence import create_protected_merkle_evidence_router
from secure_vector_db.crypto.merkle_audit import JsonlMerkleAuditLog
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore


def should_enable_merkle_api(env: dict[str, str] | None = None) -> bool:
    """Indica si la API Merkle debe habilitarse."""
    source = os.environ if env is None else env
    value = source.get("SECURE_VECTOR_DB_ENABLE_MERKLE_API", "false").strip().lower()
    return value in {"1", "true", "yes", "si"}


def install_merkle_evidence_routes(
    app: FastAPI,
    database_path: str | Path,
    audit_log_path: str | Path | None = None,
    enabled: bool = True,
) -> bool:
    """Instala rutas Merkle protegidas en una aplicacion FastAPI."""
    if not enabled:
        return False
    store = SQLiteMerkleNodeStore(database_path)
    audit_log = JsonlMerkleAuditLog(audit_log_path) if audit_log_path is not None else None
    app.include_router(create_protected_merkle_evidence_router(store=store, audit_log=audit_log))
    return True


def install_merkle_evidence_routes_from_env(app: FastAPI) -> bool:
    """Instala rutas Merkle usando variables de entorno."""
    if not should_enable_merkle_api():
        return False
    database_path = os.environ.get("SECURE_VECTOR_DB_MERKLE_DB_PATH", "secure-vector-db-merkle.sqlite")
    audit_log_path = os.environ.get("SECURE_VECTOR_DB_MERKLE_AUDIT_LOG", "reports/merkle-audit.jsonl")
    return install_merkle_evidence_routes(app, database_path, audit_log_path, enabled=True)


def merkle_production_settings(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Devuelve configuracion segura de integracion Merkle."""
    source = os.environ if env is None else env
    return {
        "enabled": should_enable_merkle_api(dict(source)),
        "database_path": source.get("SECURE_VECTOR_DB_MERKLE_DB_PATH", ""),
        "audit_log_configured": bool(source.get("SECURE_VECTOR_DB_MERKLE_AUDIT_LOG", "")),
    }
