"""Componentes de almacenamiento de SecureVectorDB."""

from secure_vector_db.storage.contracts import (
    POSTGRES_BACKEND_INFO,
    SQLITE_BACKEND_INFO,
    PersistentRecordStore,
    StorageBackendInfo,
    VolatileRecordStore,
    available_storage_backends,
)
from secure_vector_db.storage.factory import create_persistent_record_store
from secure_vector_db.storage.record_store import Record, RecordStore
from secure_vector_db.storage.sqlite_store import SQLiteRecordStore

__all__ = [
    "POSTGRES_BACKEND_INFO",
    "SQLITE_BACKEND_INFO",
    "PersistentRecordStore",
    "Record",
    "RecordStore",
    "SQLiteRecordStore",
    "StorageBackendInfo",
    "VolatileRecordStore",
    "available_storage_backends",
    "create_persistent_record_store",
]
