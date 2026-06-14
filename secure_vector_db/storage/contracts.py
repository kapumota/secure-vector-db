"""Contratos de almacenamiento para backends persistentes y volatiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

from secure_vector_db.storage.record_store import Record


@runtime_checkable
class PersistentRecordStore(Protocol):
    """Contrato minimo para un backend persistente de registros."""

    path: Path

    def upsert(self, record: Record) -> None:
        """Guarda o reemplaza un registro."""

    def delete(self, record_id: int) -> bool:
        """Elimina un registro por ID."""

    def get(self, record_id: int) -> Optional[Record]:
        """Lee un registro por ID."""

    def all(self) -> List[Record]:
        """Lista todos los registros en orden estable."""

    def count(self) -> int:
        """Devuelve cantidad de registros persistidos."""

    def set_meta(self, key: str, value: str) -> None:
        """Guarda metadata de almacenamiento."""

    def get_meta(self, key: str, default: str = "") -> str:
        """Lee metadata de almacenamiento."""

    def close(self) -> None:
        """Cierra recursos asociados al backend."""


@runtime_checkable
class VolatileRecordStore(Protocol):
    """Contrato minimo para un store volatil en memoria."""

    def insert(self, record: Record) -> None:
        """Inserta o reemplaza un registro en memoria."""

    def delete(self, record_id: int) -> bool:
        """Elimina un registro por ID."""

    def get(self, record_id: int) -> Optional[Record]:
        """Lee un registro por ID."""

    def all(self) -> List[Record]:
        """Lista todos los registros en orden estable."""

    def __len__(self) -> int:
        """Devuelve cantidad de registros en memoria."""


@dataclass(frozen=True)
class StorageBackendInfo:
    """Describe capacidades de un backend de almacenamiento."""

    name: str
    durable: bool
    vector_native: bool
    metadata_native: bool
    consistency_model: str
    status: str


SQLITE_BACKEND_INFO = StorageBackendInfo(
    name="sqlite",
    durable=True,
    vector_native=False,
    metadata_native=True,
    consistency_model="single_process_wal",
    status="stable",
)

POSTGRES_BACKEND_INFO = StorageBackendInfo(
    name="postgres_pgvector",
    durable=True,
    vector_native=True,
    metadata_native=True,
    consistency_model="external_database",
    status="planned",
)


def available_storage_backends() -> List[StorageBackendInfo]:
    """Devuelve backends conocidos por la arquitectura."""
    return [SQLITE_BACKEND_INFO, POSTGRES_BACKEND_INFO]
