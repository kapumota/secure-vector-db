"""Evidencia verificable para Merkle incremental."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from secure_vector_db.crypto.merkle_persistence import (
    MerkleRecoveryError,
    SQLiteMerkleNodeStore,
)

MerkleEvidenceStatus = Literal[
    "valid",
    "corrupted",
    "missing_nodes",
    "recovered",
    "empty",
]


@dataclass(frozen=True)
class MerkleEvidenceReport:
    """Reporte publico y seguro de evidencia Merkle."""

    status: MerkleEvidenceStatus
    root_hex: str
    leaf_count: int
    node_count: int
    recovered_from: str
    algorithm: str
    storage_backend: str
    evidence_version: str
    message: str

    def to_dict(self) -> dict[str, str | int]:
        """Convierte el reporte a diccionario serializable."""
        return asdict(self)


def build_merkle_evidence_report(
    store: SQLiteMerkleNodeStore,
    recover_missing_nodes: bool = False,
) -> MerkleEvidenceReport:
    """Construye evidencia Merkle desde almacenamiento persistente."""
    try:
        leaf_digests = store.load_leaf_digests()
        persisted_root = store.load_root_hex()
        node_count = store.count_nodes()

        if not leaf_digests and not persisted_root:
            return MerkleEvidenceReport(
                status="empty",
                root_hex="",
                leaf_count=0,
                node_count=0,
                recovered_from="empty",
                algorithm="sha256-domain-separated",
                storage_backend="sqlite",
                evidence_version="1",
                message="arbol Merkle vacio",
            )

        if recover_missing_nodes and leaf_digests and node_count == 0:
            rebuilt = store.rebuild_missing_nodes()
            return MerkleEvidenceReport(
                status="recovered",
                root_hex=rebuilt.root_hex,
                leaf_count=rebuilt.leaves,
                node_count=rebuilt.nodes,
                recovered_from="leaves",
                algorithm="sha256-domain-separated",
                storage_backend="sqlite",
                evidence_version="1",
                message="nodos Merkle reconstruidos desde hojas persistidas",
            )

        tree, stats = store.recover_tree()

        if leaf_digests and node_count == 0:
            return MerkleEvidenceReport(
                status="missing_nodes",
                root_hex=tree.root_hex,
                leaf_count=stats.leaves,
                node_count=0,
                recovered_from=stats.recovered_from,
                algorithm="sha256-domain-separated",
                storage_backend="sqlite",
                evidence_version="1",
                message="faltan nodos internos Merkle, recovery posible desde hojas",
            )

        return MerkleEvidenceReport(
            status="valid",
            root_hex=tree.root_hex,
            leaf_count=stats.leaves,
            node_count=stats.nodes,
            recovered_from=stats.recovered_from,
            algorithm="sha256-domain-separated",
            storage_backend="sqlite",
            evidence_version="1",
            message="integridad Merkle valida",
        )
    except MerkleRecoveryError:
        return MerkleEvidenceReport(
            status="corrupted",
            root_hex=store.load_root_hex(),
            leaf_count=len(store.load_leaf_digests()),
            node_count=store.count_nodes(),
            recovered_from="error",
            algorithm="sha256-domain-separated",
            storage_backend="sqlite",
            evidence_version="1",
            message="integridad Merkle corrupta",
        )


def verify_merkle_evidence(store: SQLiteMerkleNodeStore) -> bool:
    """Verifica si la evidencia Merkle esta valida."""
    return build_merkle_evidence_report(store).status == "valid"


def export_merkle_evidence_json(
    store: SQLiteMerkleNodeStore,
    output_path: str | Path,
    recover_missing_nodes: bool = False,
) -> MerkleEvidenceReport:
    """Exporta evidencia Merkle en JSON."""
    report = build_merkle_evidence_report(
        store=store,
        recover_missing_nodes=recover_missing_nodes,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
