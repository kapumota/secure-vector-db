"""Persistencia SQLite para modelos de indice aprendido."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Sequence

from secure_vector_db.errors import StorageError
from secure_vector_db.storage.sqlite_store import SQLiteRecordStore


FORMAT_VERSION = 1
META_PREFIX = "learned_index"


class LearnedIndexStore:
    """Guarda y carga segmentos del indice aprendido en SQLite."""

    def __init__(self, store: SQLiteRecordStore) -> None:
        """Inicializa el almacenamiento sobre una base SQLite existente."""
        self._store = store
        self._init_schema()

    @staticmethod
    def key_fingerprint(keys: Sequence[int]) -> str:
        """Calcula una huella estable para la distribucion de claves."""
        payload = ",".join(str(key) for key in keys)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, index_name: str, keys: Sequence[int], snapshot: Dict[str, Any]) -> None:
        """Persiste metadata y segmentos del modelo aprendido."""
        metadata = dict(snapshot["metadata"])
        segments = list(snapshot["segments"])
        metadata.update(
            {
                "index_name": index_name,
                "format_version": FORMAT_VERSION,
                "key_fingerprint": self.key_fingerprint(keys),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        try:
            with self._store._lock, self._store.conn:
                self._store.conn.execute(
                    "DELETE FROM learned_index_segments WHERE index_name=?",
                    (index_name,),
                )
                for segment in segments:
                    self._store.conn.execute(
                        """
                        INSERT INTO learned_index_segments(
                            index_name,
                            segment_id,
                            start_key,
                            end_key,
                            start_position,
                            end_position,
                            slope,
                            intercept,
                            max_error,
                            avg_error
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            index_name,
                            int(segment["segment_id"]),
                            int(segment["start_key"]),
                            int(segment["end_key"]),
                            int(segment["start_position"]),
                            int(segment["end_position"]),
                            float(segment["slope"]),
                            float(segment["intercept"]),
                            int(segment["max_error"]),
                            float(segment["avg_error"]),
                        ),
                    )
                self._store.conn.execute(
                    "INSERT INTO kv_meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (self._meta_key(index_name), json.dumps(metadata, ensure_ascii=False, sort_keys=True)),
                )
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo persistir indice aprendido {index_name}: {exc}") from exc

    def load(self, index_name: str) -> Dict[str, Any] | None:
        """Carga metadata y segmentos persistidos si existen."""
        try:
            metadata_raw = self._store.get_meta(self._meta_key(index_name), "")
            if not metadata_raw:
                return None
            metadata = json.loads(metadata_raw)

            with self._store._lock:
                rows = self._store.conn.execute(
                    """
                    SELECT
                        segment_id,
                        start_key,
                        end_key,
                        start_position,
                        end_position,
                        slope,
                        intercept,
                        max_error,
                        avg_error
                    FROM learned_index_segments
                    WHERE index_name=?
                    ORDER BY segment_id ASC
                    """,
                    (index_name,),
                ).fetchall()

            segments = [dict(row) for row in rows]
            if int(metadata.get("segments", 0)) != len(segments):
                return None
            return {"metadata": metadata, "segments": segments}
        except (json.JSONDecodeError, sqlite3.Error) as exc:
            raise StorageError(f"No se pudo cargar indice aprendido {index_name}: {exc}") from exc

    def delete(self, index_name: str) -> None:
        """Elimina metadata y segmentos persistidos."""
        try:
            with self._store._lock, self._store.conn:
                self._store.conn.execute("DELETE FROM learned_index_segments WHERE index_name=?", (index_name,))
                self._store.conn.execute("DELETE FROM kv_meta WHERE key=?", (self._meta_key(index_name),))
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo eliminar indice aprendido {index_name}: {exc}") from exc

    def has_index(self, index_name: str) -> bool:
        """Indica si existe metadata persistida para el indice."""
        return bool(self._store.get_meta(self._meta_key(index_name), ""))

    def _init_schema(self) -> None:
        # Crea la tabla de segmentos aprendidos si no existe.
        try:
            with self._store._lock, self._store.conn:
                self._store.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS learned_index_segments (
                        index_name TEXT NOT NULL,
                        segment_id INTEGER NOT NULL,
                        start_key INTEGER NOT NULL,
                        end_key INTEGER NOT NULL,
                        start_position INTEGER NOT NULL,
                        end_position INTEGER NOT NULL,
                        slope REAL NOT NULL,
                        intercept REAL NOT NULL,
                        max_error INTEGER NOT NULL,
                        avg_error REAL NOT NULL,
                        PRIMARY KEY(index_name, segment_id)
                    )
                    """
                )
        except sqlite3.Error as exc:
            raise StorageError(f"No se pudo inicializar persistencia de indice aprendido: {exc}") from exc

    @staticmethod
    def _meta_key(index_name: str) -> str:
        # Usa kv_meta para metadata compacta del modelo aprendido.
        return f"{META_PREFIX}:{index_name}:metadata"
