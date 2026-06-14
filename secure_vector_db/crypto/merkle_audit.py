"""Auditoria para evidencia Merkle verificable."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

MerkleAuditStatus = Literal["valid", "corrupted", "missing_nodes", "recovered", "empty"]


@dataclass(frozen=True)
class MerkleAuditEvent:
    """Evento de auditoria Merkle sin datos sensibles."""

    action: str
    status: MerkleAuditStatus
    root_hex: str
    leaf_count: int
    node_count: int
    message: str
    timestamp_unix: float

    def to_dict(self) -> dict[str, str | int | float]:
        """Convierte el evento a diccionario JSON seguro."""
        return cast(dict[str, str | int | float], asdict(self))


class JsonlMerkleAuditLog:
    """Log JSONL para eventos Merkle."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, event: MerkleAuditEvent) -> None:
        """Agrega evento al log JSONL."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")

    def read_events(self) -> list[MerkleAuditEvent]:
        """Lee eventos persistidos para pruebas y diagnostico."""
        if not self.path.exists():
            return []
        events: list[MerkleAuditEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            events.append(
                MerkleAuditEvent(
                    action=str(payload["action"]),
                    status=cast(MerkleAuditStatus, str(payload["status"])),
                    root_hex=str(payload["root_hex"]),
                    leaf_count=int(payload["leaf_count"]),
                    node_count=int(payload["node_count"]),
                    message=str(payload["message"]),
                    timestamp_unix=float(payload["timestamp_unix"]),
                )
            )
        return events


def build_merkle_audit_event(
    action: str,
    status: MerkleAuditStatus,
    root_hex: str,
    leaf_count: int,
    node_count: int,
    message: str,
) -> MerkleAuditEvent:
    """Construye evento de auditoria Merkle."""
    return MerkleAuditEvent(
        action=action,
        status=status,
        root_hex=root_hex,
        leaf_count=leaf_count,
        node_count=node_count,
        message=message,
        timestamp_unix=time.time(),
    )


def append_merkle_audit_event(
    audit_log: JsonlMerkleAuditLog | None,
    action: str,
    status: MerkleAuditStatus,
    root_hex: str,
    leaf_count: int,
    node_count: int,
    message: str,
) -> MerkleAuditEvent:
    """Registra evento Merkle si existe log configurado."""
    event = build_merkle_audit_event(action, status, root_hex, leaf_count, node_count, message)
    if audit_log is not None:
        audit_log.append(event)
    return event
