from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Optional

from secure_vector_db.errors import StorageError
from secure_vector_db.storage.record_store import Record

SCHEMA_VERSION = 1

class SQLiteRecordStore:
    """Almacenamiento robusto basado en SQLite con registro de transacciones (WAL), transacciones explícitas y acceso seguro para subprocesos."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = RLock()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self._init_schema()
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo abrir SQLite en {self.path}: {exc}") from exc

    def _init_schema(self) -> None:
        try:
            with self._lock, self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS records (
                        record_id INTEGER PRIMARY KEY,
                        text TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        embedding_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS kv_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                self.conn.execute(
                    "INSERT OR IGNORE INTO kv_meta(key, value) VALUES (?, ?)",
                    ("schema_version", str(SCHEMA_VERSION)),
                )
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo inicializar el esquema SQLite: {exc}") from exc

    def upsert(self, record: Record) -> None:
        try:
            with self._lock, self.conn:
                self.conn.execute(
                    """
                    INSERT INTO records(record_id, text, metadata_json, embedding_json, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(record_id) DO UPDATE SET
                        text=excluded.text,
                        metadata_json=excluded.metadata_json,
                        embedding_json=excluded.embedding_json,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        record.record_id,
                        record.text,
                        json.dumps(record.metadata, ensure_ascii=False, sort_keys=True),
                        json.dumps(record.embedding, ensure_ascii=False),
                    ),
                )
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo guardar record_id={record.record_id}: {exc}") from exc

    def delete(self, record_id: int) -> bool:
        try:
            with self._lock, self.conn:
                cur = self.conn.execute("DELETE FROM records WHERE record_id=?", (record_id,))
            return cur.rowcount > 0
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo borrar record_id={record_id}: {exc}") from exc

    def get(self, record_id: int) -> Optional[Record]:
        try:
            with self._lock:
                row = self.conn.execute("SELECT * FROM records WHERE record_id=?", (record_id,)).fetchone()
            return self._row_to_record(row) if row else None
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo leer record_id={record_id}: {exc}") from exc

    def all(self) -> list[Record]:
        try:
            with self._lock:
                rows = self.conn.execute("SELECT * FROM records ORDER BY record_id ASC").fetchall()
            return [self._row_to_record(row) for row in rows]
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo leer la base SQLite: {exc}") from exc

    def count(self) -> int:
        try:
            with self._lock:
                return int(self.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0])
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo contar registros: {exc}") from exc

    def set_meta(self, key: str, value: str) -> None:
        try:
            with self._lock, self.conn:
                self.conn.execute(
                    "INSERT INTO kv_meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo guardar metadata {key}: {exc}") from exc

    def get_meta(self, key: str, default: str = "") -> str:
        try:
            with self._lock:
                row = self.conn.execute("SELECT value FROM kv_meta WHERE key=?", (key,)).fetchone()
            return str(row["value"]) if row else default
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo leer metadata {key}: {exc}") from exc

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> Record:
        return Record(
            record_id=int(row["record_id"]),
            text=str(row["text"]),
            metadata=json.loads(row["metadata_json"]),
            embedding=[float(x) for x in json.loads(row["embedding_json"])],
        )
