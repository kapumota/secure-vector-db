from __future__ import annotations

from pathlib import Path

import pytest

from secure_vector_db.database import SecureVectorDB
from secure_vector_db.storage.contracts import (
    PersistentRecordStore,
    VolatileRecordStore,
    available_storage_backends,
)
from secure_vector_db.storage.factory import create_persistent_record_store
from secure_vector_db.storage.record_store import Record, RecordStore
from secure_vector_db.storage.sqlite_store import SQLiteRecordStore


def make_record(record_id: int = 1) -> Record:
    return Record(
        record_id=record_id,
        text=f"documento {record_id}",
        metadata={"grupo": "storage"},
        embedding=[0.1, 0.2, 0.3],
    )


def test_sqlite_store_satisfies_persistent_contract(tmp_path: Path) -> None:
    path = tmp_path / "contract.sqlite"
    store = SQLiteRecordStore(path)

    assert isinstance(store, PersistentRecordStore)

    record = make_record(7)
    store.upsert(record)

    assert store.count() == 1
    assert store.get(7) == record
    assert [item.record_id for item in store.all()] == [7]

    store.set_meta("clave", "valor")
    assert store.get_meta("clave") == "valor"

    assert store.delete(7) is True
    assert store.get(7) is None
    assert store.count() == 0

    store.close()


def test_record_store_satisfies_volatile_contract() -> None:
    store = RecordStore()

    assert isinstance(store, VolatileRecordStore)

    record = make_record(3)
    store.insert(record)

    assert len(store) == 1
    assert store.get(3) == record
    assert [item.record_id for item in store.all()] == [3]
    assert store.delete(3) is True
    assert len(store) == 0


def test_storage_factory_creates_sqlite_backend(tmp_path: Path) -> None:
    path = tmp_path / "factory.sqlite"
    store = create_persistent_record_store("sqlite", path)

    assert isinstance(store, PersistentRecordStore)

    store.upsert(make_record(11))
    assert store.get(11) is not None

    store.close()


def test_storage_factory_rejects_unknown_backend(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="backend de almacenamiento no soportado"):
        create_persistent_record_store("postgres", tmp_path / "db.sqlite")


def test_available_storage_backends_documents_sqlite_and_future_postgres() -> None:
    backends = {backend.name: backend for backend in available_storage_backends()}

    assert backends["sqlite"].status == "stable"
    assert backends["sqlite"].durable is True
    assert backends["postgres_pgvector"].status == "planned"
    assert backends["postgres_pgvector"].vector_native is True


def test_secure_vector_db_open_keeps_sqlite_compatibility(tmp_path: Path) -> None:
    path = tmp_path / "svdb.sqlite"

    db = SecureVectorDB.open(path)
    db.insert(1, "documento persistente", {"fase": 10})
    root = db.root_hash
    db.close()

    reopened = SecureVectorDB.open(path)
    record = reopened.search_by_id(1)

    assert record is not None
    assert record.metadata["fase"] == 10
    assert reopened.root_hash == root
    assert reopened.verify_dataset() is True

    reopened.close()
