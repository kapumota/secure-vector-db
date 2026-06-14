"""Router API opcional para evidencia Merkle."""

from __future__ import annotations

from fastapi import APIRouter

from secure_vector_db.crypto.merkle_evidence import (
    build_merkle_evidence_report,
    verify_merkle_evidence,
)
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore


def create_merkle_evidence_router(store: SQLiteMerkleNodeStore) -> APIRouter:
    """Crea router FastAPI para evidencia Merkle verificable."""
    router = APIRouter(prefix="/merkle", tags=["merkle"])

    @router.get("/root")
    def get_merkle_root() -> dict[str, str | int]:
        """Devuelve raiz Merkle actual y conteos publicos."""
        report = build_merkle_evidence_report(store)
        return {
            "root_hex": report.root_hex,
            "status": report.status,
            "leaf_count": report.leaf_count,
            "node_count": report.node_count,
        }

    @router.get("/verify")
    def verify_merkle_root() -> dict[str, str | bool]:
        """Verifica integridad Merkle persistida."""
        report = build_merkle_evidence_report(store)
        return {
            "valid": verify_merkle_evidence(store),
            "status": report.status,
            "message": report.message,
        }

    @router.get("/evidence")
    def get_merkle_evidence(recover_missing_nodes: bool = False) -> dict[str, str | int]:
        """Devuelve reporte de evidencia Merkle."""
        report = build_merkle_evidence_report(
            store=store,
            recover_missing_nodes=recover_missing_nodes,
        )
        return report.to_dict()

    return router
