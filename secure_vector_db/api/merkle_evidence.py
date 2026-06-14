"""Router API opcional para evidencia Merkle."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from secure_vector_db.crypto.merkle_audit import JsonlMerkleAuditLog, append_merkle_audit_event
from secure_vector_db.crypto.merkle_evidence import build_merkle_evidence_report, verify_merkle_evidence
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore


def _dependencies_from(callable_dependency: Callable[..., Any] | None) -> list[Any]:
    """Convierte dependencia opcional a lista FastAPI."""
    if callable_dependency is None:
        return []
    return [Depends(callable_dependency)]


def create_merkle_evidence_router(
    store: SQLiteMerkleNodeStore,
    audit_log: JsonlMerkleAuditLog | None = None,
    read_dependency: Callable[..., Any] | None = None,
    admin_dependency: Callable[..., Any] | None = None,
) -> APIRouter:
    """Crea router FastAPI para evidencia Merkle verificable."""
    router = APIRouter(prefix="/merkle", tags=["merkle"])

    @router.get("/root", dependencies=_dependencies_from(read_dependency))
    def get_merkle_root() -> dict[str, str | int]:
        """Devuelve raiz Merkle actual y conteos publicos."""
        report = build_merkle_evidence_report(store)
        append_merkle_audit_event(
            audit_log, "root", report.status, report.root_hex,
            report.leaf_count, report.node_count, report.message,
        )
        return {
            "root_hex": report.root_hex,
            "status": report.status,
            "leaf_count": report.leaf_count,
            "node_count": report.node_count,
        }

    @router.get("/verify", dependencies=_dependencies_from(admin_dependency))
    def verify_merkle_root() -> dict[str, str | bool]:
        """Verifica integridad Merkle persistida."""
        report = build_merkle_evidence_report(store)
        valid = verify_merkle_evidence(store)
        append_merkle_audit_event(
            audit_log, "verify", report.status, report.root_hex,
            report.leaf_count, report.node_count, report.message,
        )
        return {"valid": valid, "status": report.status, "message": report.message}

    @router.get("/evidence", dependencies=_dependencies_from(admin_dependency))
    def get_merkle_evidence(recover_missing_nodes: bool = False) -> dict[str, str | int]:
        """Devuelve reporte de evidencia Merkle."""
        report = build_merkle_evidence_report(store, recover_missing_nodes=recover_missing_nodes)
        append_merkle_audit_event(
            audit_log, "evidence", report.status, report.root_hex,
            report.leaf_count, report.node_count, report.message,
        )
        return report.to_dict()

    return router


def create_protected_merkle_evidence_router(
    store: SQLiteMerkleNodeStore,
    audit_log: JsonlMerkleAuditLog | None = None,
) -> APIRouter:
    """Crea router Merkle protegido con scopes basicos."""
    from secure_vector_db.api.auth_scopes import require_admin_scope, require_read_scope

    return create_merkle_evidence_router(
        store=store,
        audit_log=audit_log,
        read_dependency=require_read_scope,
        admin_dependency=require_admin_scope,
    )
