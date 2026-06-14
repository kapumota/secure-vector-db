"""Integracion Merkle con flujos reales de escritura."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from secure_vector_db.crypto.incremental_merkle import MerkleUpdateResult
from secure_vector_db.crypto.merkle_audit import JsonlMerkleAuditLog, append_merkle_audit_event
from secure_vector_db.crypto.merkle_persistence import MerklePersistenceStats, SQLiteMerkleNodeStore
from secure_vector_db.storage.record_store import Record


@dataclass(frozen=True)
class MerkleWriteResult:
    """Resultado de integracion Merkle con escritura real."""

    operation: str
    mode: str
    root_hex: str
    leaf_count: int
    node_count: int
    persisted: bool

    def to_dict(self) -> dict[str, str | int | bool]:
        """Convierte el resultado a diccionario JSON."""
        return asdict(self)


class MerkleWriteIntegrator:
    """Integra escrituras reales con Merkle incremental persistente."""

    def __init__(
        self,
        database_path: str | Path,
        audit_log_path: str | Path | None = None,
    ) -> None:
        self.store = SQLiteMerkleNodeStore(database_path)
        self.store.initialize()
        self.tree, _ = self.store.recover_tree()
        self.audit_log = JsonlMerkleAuditLog(audit_log_path) if audit_log_path else None

    @property
    def root_hex(self) -> str:
        """Raiz Merkle actual."""
        return self.tree.root_hex

    def rebuild_from_records(
        self,
        records: Iterable[Record],
        operation: str = "rebuild",
    ) -> MerkleWriteResult:
        """Reconstruye Merkle desde registros reales."""
        update = self.tree.rebuild(
            (record.record_id, record.canonical()) for record in records
        )
        stats = self.store.save_tree(self.tree)
        return self._persist_result(operation=operation, update=update, stats=stats)

    def apply_insert(self, record: Record) -> MerkleWriteResult:
        """Aplica insert o reemplazo real a Merkle."""
        update = self.tree.update_leaf(record.record_id, record.canonical())
        stats = self.store.save_tree(self.tree)
        return self._persist_result(operation="insert", update=update, stats=stats)

    def apply_delete(self, record_id: int) -> MerkleWriteResult:
        """Aplica delete real a Merkle."""
        update = self.tree.delete_leaf(record_id)
        stats = self.store.save_tree(self.tree)
        return self._persist_result(operation="delete", update=update, stats=stats)

    def verify_integrity(self) -> bool:
        """Verifica Merkle persistente contra hojas persistidas."""
        return self.store.verify_integrity() and self.tree.verify_against_full_rebuild()

    def _persist_result(
        self,
        operation: str,
        update: MerkleUpdateResult,
        stats: MerklePersistenceStats,
    ) -> MerkleWriteResult:
        """Registra resultado persistido y auditoria."""
        append_merkle_audit_event(
            audit_log=self.audit_log,
            action="write-" + operation,
            status="valid",
            root_hex=update.root_hex,
            leaf_count=stats.leaves,
            node_count=stats.nodes,
            message="Merkle actualizado desde escritura real con modo " + update.mode,
        )
        return MerkleWriteResult(
            operation=operation,
            mode=update.mode,
            root_hex=update.root_hex,
            leaf_count=stats.leaves,
            node_count=stats.nodes,
            persisted=True,
        )


def is_merkle_write_integration_enabled(env: dict[str, str] | None = None) -> bool:
    """Indica si la integracion de escrituras reales esta activa."""
    source = os.environ if env is None else env
    value = source.get("SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION", "")
    return value.lower() in {"1", "true", "yes", "on"}


def merkle_write_database_path(
    storage_path: str | Path | None,
    env: dict[str, str] | None = None,
) -> Path | None:
    """Calcula ruta SQLite para Merkle de escrituras reales."""
    source = os.environ if env is None else env
    configured = source.get("SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH")
    if configured:
        return Path(configured)

    legacy_configured = source.get("SECURE_VECTOR_DB_MERKLE_DB_PATH")
    if legacy_configured:
        return Path(legacy_configured)

    if storage_path is None:
        return None

    base = Path(storage_path)
    if base.suffix:
        return base.with_suffix(".merkle.sqlite")
    return Path(str(base) + ".merkle.sqlite")


def merkle_write_audit_log_path(env: dict[str, str] | None = None) -> Path | None:
    """Calcula ruta de auditoria JSONL para escrituras reales."""
    source = os.environ if env is None else env
    configured = source.get("SECURE_VECTOR_DB_MERKLE_WRITE_AUDIT_LOG")
    if configured:
        return Path(configured)

    legacy_configured = source.get("SECURE_VECTOR_DB_MERKLE_AUDIT_LOG")
    if legacy_configured:
        return Path(legacy_configured)

    return None


def build_merkle_write_integrator_from_env(
    storage_path: str | Path | None,
) -> MerkleWriteIntegrator | None:
    """Construye integrador Merkle desde variables de entorno."""
    if not is_merkle_write_integration_enabled():
        return None

    database_path = merkle_write_database_path(storage_path)
    if database_path is None:
        return None

    return MerkleWriteIntegrator(
        database_path=database_path,
        audit_log_path=merkle_write_audit_log_path(),
    )
