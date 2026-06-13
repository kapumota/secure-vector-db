from __future__ import annotations

import hashlib
import json
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

from secure_vector_db.errors import IntegrityError, RecordNotFoundError, ValidationError
from secure_vector_db.indexes.bplus_tree import BPlusTree
from secure_vector_db.indexes.ordered_index_router import OrderedIndexRouter
from secure_vector_db.indexes.factory import create_vector_index
from secure_vector_db.ml.embeddings import create_embedding_model
from secure_vector_db.storage.record_store import Record, RecordStore
from secure_vector_db.storage.sqlite_store import SQLiteRecordStore

class SimpleMerkle:
    """Merkle Tree mínimo para raíz verificable usando SHA-256."""

    @staticmethod
    def _h(data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    @classmethod
    def root_hex(cls, items: List[str]) -> str:
        if not items:
            return ""
        level = [cls._h(x.encode("utf-8")) for x in items]
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [cls._h(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        return level[0].hex()

class SecureVectorDB:
    """Base de datos vectorial verificable.

    v3 añade persistencia durable en SQLite. Los registros sobreviven reinicios
    del proceso; los índices B+ Tree y vectorial se reconstruyen desde SQLite al
    abrir la base. Los embeddings son hash-based y no corresponden a un LLM real.
    """

    def __init__(
        self,
        embedding_dim: int = 8,
        bplus_order: int = 4,
        storage_path: str | Path | None = None,
        vector_index: str = "kd_tree",
        embedding_model: str = "hash",
        embedding_model_name: str | None = None,
        learned_index_enabled: bool = False,
        learned_max_error: int = 64,
    ) -> None:
        if embedding_dim <= 0:
            raise ValidationError("embedding_dim debe ser positivo")
        if bplus_order < 3:
            raise ValidationError("bplus_order debe ser >= 3")
        if learned_max_error < 0:
            raise ValidationError("learned_max_error debe ser >= 0")
        self.bplus_order = bplus_order
        self.learned_max_error = learned_max_error
        self.vector_index_backend = vector_index
        self.embedding_model_backend = embedding_model
        self.embedding_model_name = embedding_model_name
        self.embedder = create_embedding_model(embedding_model, embedding_dim, embedding_model_name)
        self.embedding_dim = self.embedder.dim
        self.id_index = BPlusTree[int, int](bplus_order)
        self.ordered_index = OrderedIndexRouter(self.id_index)
        self.vector_index = create_vector_index(embedding_dim, vector_index)
        self._lock = RLock()
        self._durable: SQLiteRecordStore | None = SQLiteRecordStore(storage_path) if storage_path else None
        self.store = RecordStore()
        self._root_hash = ""
        if self._durable:
            self._load_from_durable()
        else:
            self._rebuild_indexes()
        if learned_index_enabled:
            self.train_learned_index(learned_max_error)

    @classmethod
    def open(
        cls,
        path: str | Path,
        embedding_dim: int = 8,
        bplus_order: int = 4,
        vector_index: str = "kd_tree",
        embedding_model: str = "hash",
        embedding_model_name: str | None = None,
        learned_index_enabled: bool = False,
        learned_max_error: int = 64,
    ) -> "SecureVectorDB":
        return cls(
            embedding_dim=embedding_dim,
            bplus_order=bplus_order,
            storage_path=path,
            vector_index=vector_index,
            embedding_model=embedding_model,
            embedding_model_name=embedding_model_name,
            learned_index_enabled=learned_index_enabled,
            learned_max_error=learned_max_error,
        )

    def _load_from_durable(self) -> None:
        assert self._durable is not None
        for record in self._durable.all():
            self.store.insert(record)
        self._rebuild_indexes()
        saved_root = self._durable.get_meta("root_hash", "")
        computed = self.compute_root_hash()
        self._root_hash = saved_root if saved_root or len(self.store) else computed

    def _sync_root(self) -> None:
        self._root_hash = self.compute_root_hash()
        if self._durable:
            self._durable.set_meta("root_hash", self._root_hash)
            self._durable.set_meta("embedding_dim", str(self.embedding_dim))
            self._durable.set_meta("bplus_order", str(self.bplus_order))
            self._durable.set_meta("vector_index", self.vector_index.backend_name)
            self._durable.set_meta("embedding_model", self.embedder.name)
            if self.embedding_model_name:
                self._durable.set_meta("embedding_model_name", self.embedding_model_name)

    def _rebuild_indexes(self) -> None:
        """Reconstruye todos los índices desde el store.

        Esta operación es O(n) y queda reservada para cargas iniciales,
        importaciones y recuperación desde snapshots. Las escrituras normales
        usan _index_record() / _remove_from_indexes() para evitar reconstruir
        toda la estructura después de cada insert/delete.
        """
        self.id_index = BPlusTree[int, int](self.bplus_order)
        self.ordered_index = OrderedIndexRouter(self.id_index)
        self.vector_index = create_vector_index(self.embedding_dim, self.vector_index_backend)
        records = self.store.all()
        for record in records:
            self.id_index.insert(record.record_id, record.record_id)
        self.vector_index.rebuild((record.record_id, record.embedding) for record in records)

    def _index_record(self, record: Record) -> None:
        """Actualiza incrementalmente los índices para un registro insertado/reemplazado."""
        self.id_index.insert(record.record_id, record.record_id)
        self.vector_index.insert(record.record_id, record.embedding)

    def _remove_from_indexes(self, record_id: int) -> None:
        """Elimina incrementalmente un registro de los índices activos."""
        self.id_index.delete(record_id)
        self.vector_index.delete(record_id)

    @staticmethod
    def _validate_record_input(record_id: int, text: str) -> None:
        if not isinstance(record_id, int) or record_id < 0:
            raise ValidationError("record_id debe ser un entero no negativo")
        if not isinstance(text, str) or not text.strip():
            raise ValidationError("text no puede estar vacío")

    def insert(self, record_id: int, text: str, metadata: Optional[Dict[str, Any]] = None) -> Record:
        with self._lock:
            self._validate_record_input(record_id, text)
            if metadata is not None and not isinstance(metadata, dict):
                raise ValidationError("metadata debe ser un objeto/diccionario")
            embedding = self.embedder.encode(text)
            record = Record(record_id=record_id, text=text, metadata=metadata or {}, embedding=embedding)
            if self._durable:
                self._durable.upsert(record)
            self.store.insert(record)
            self._index_record(record)
            self._disable_learned_index("datos modificados despues del entrenamiento")
            self._sync_root()
            return record

    def delete(self, record_id: int) -> bool:
        with self._lock:
            if not isinstance(record_id, int) or record_id < 0:
                raise ValidationError("record_id debe ser un entero no negativo")
            deleted = self.store.delete(record_id)
            if self._durable:
                deleted = self._durable.delete(record_id) or deleted
            if deleted:
                self._remove_from_indexes(record_id)
                self._disable_learned_index("datos modificados despues del entrenamiento")
                self._sync_root()
            return deleted

    def search_by_id(self, record_id: int) -> Optional[Record]:
        with self._lock:
            if not isinstance(record_id, int) or record_id < 0:
                raise ValidationError("record_id debe ser un entero no negativo")
            found_id = self.ordered_index.find(record_id)
            if found_id is None:
                return None
            return self.store.get(found_id)

    def train_learned_index(self, max_error: int = 64) -> Dict[str, Any]:
        """Entrena el indice aprendido ordenado sobre los IDs actuales."""
        with self._lock:
            if max_error < 0:
                raise ValidationError("max_error debe ser >= 0")
            keys = [record.record_id for record in self.store.all()]
            self.learned_max_error = max_error
            return self.ordered_index.train(keys, max_error)

    def ordered_index_stats(self) -> Dict[str, Any]:
        """Devuelve metricas del indice ordenado hibrido."""
        with self._lock:
            return self.ordered_index.stats()

    def _disable_learned_index(self, reason: str) -> None:
        # Desactiva el indice aprendido si los datos cambiaron.
        if self.ordered_index.enabled:
            self.ordered_index.disable(reason)

    def get_or_raise(self, record_id: int) -> Record:
        rec = self.search_by_id(record_id)
        if rec is None:
            raise RecordNotFoundError(f"record_id={record_id} no existe")
        return rec

    def search_by_range(self, start_id: int, end_id: int) -> List[Record]:
        with self._lock:
            if not isinstance(start_id, int) or not isinstance(end_id, int):
                raise ValidationError("start_id y end_id deben ser enteros")
            if start_id > end_id:
                raise ValidationError("start_id debe ser menor o igual que end_id")
            out: List[Record] = []
            for key, values in self.id_index.traverse_leaves():
                if key > end_id:
                    break
                if start_id <= key:
                    for rid in values:
                        rec = self.store.get(rid)
                        if rec:
                            out.append(rec)
            return out

    def semantic_search(self, query: str, k: int = 3) -> List[Tuple[Record, float]]:
        with self._lock:
            if not isinstance(query, str) or not query.strip():
                raise ValidationError("query no puede estar vacío")
            if k <= 0:
                raise ValidationError("k debe ser positivo")
            qv = self.embedder.encode(query)
            result = []
            for rid, dist in self.vector_index.knn(qv, k):
                rec = self.store.get(rid)
                if rec:
                    result.append((rec, dist))
            return result

    def compute_root_hash(self) -> str:
        with self._lock:
            return SimpleMerkle.root_hex([r.canonical() for r in self.store.all()])

    def verify_dataset(self) -> bool:
        with self._lock:
            return self._root_hash == self.compute_root_hash()

    def assert_integrity(self) -> None:
        if not self.verify_dataset():
            raise IntegrityError("La raíz Merkle guardada no coincide con los datos actuales")

    def tamper_text_for_demo(self, record_id: int, new_text: str) -> None:
        rec = self.get_or_raise(record_id)
        rec.text = new_text

    def save(self, path: str | Path) -> None:
        """Exporta snapshot JSON. Para persistencia real use SecureVectorDB.open(path.sqlite)."""
        payload = {
            "embedding_dim": self.embedding_dim,
            "bplus_order": self.bplus_order,
            "root_hash": self._root_hash,
            "records": self.store.to_list(),
            "embedding_note": "hash model is deterministic/offline; sentence-transformers produces real semantic embeddings when configured",
            "embedding_model": self.embedder.name,
            "embedding_model_name": self.embedding_model_name,
            "vector_index": self.vector_index.backend_name,
        }
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SecureVectorDB":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        db = cls(embedding_dim=int(payload.get("embedding_dim", 8)), bplus_order=int(payload.get("bplus_order", 4)), vector_index=str(payload.get("vector_index", "kd_tree")), embedding_model=str(payload.get("embedding_model", "hash")), embedding_model_name=payload.get("embedding_model_name"))
        for item in payload.get("records", []):
            db.store.insert(Record.from_dict(item))
        db._rebuild_indexes()
        db._root_hash = str(payload.get("root_hash", db.compute_root_hash()))
        return db

    def close(self) -> None:
        if self._durable:
            self._durable.close()

    @property
    def root_hash(self) -> str:
        return self._root_hash
