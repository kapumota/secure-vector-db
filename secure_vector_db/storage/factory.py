"""Factory de backends persistentes de almacenamiento."""

from __future__ import annotations

from pathlib import Path

from secure_vector_db.storage.contracts import PersistentRecordStore
from secure_vector_db.storage.sqlite_store import SQLiteRecordStore


def create_persistent_record_store(backend: str, path: str | Path) -> PersistentRecordStore:
    """Crea un backend persistente soportado."""
    normalized = backend.strip().lower()
    if normalized == "sqlite":
        return SQLiteRecordStore(path)
    raise ValueError(f"backend de almacenamiento no soportado: {backend}")
