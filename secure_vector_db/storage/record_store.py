from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from typing import Dict, Any, List, Optional

def normalize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza exactamente la representacion JSON persistida por SQLite."""
    if not isinstance(metadata, dict):
        raise ValueError("metadata debe ser un objeto JSON")
    # El primer paso convierte tuplas en listas y claves enteras en cadenas.
    encoded = json.dumps(metadata, ensure_ascii=False, allow_nan=False)
    decoded = json.loads(encoded)
    if not isinstance(decoded, dict):
        raise ValueError("metadata debe ser un objeto JSON")
    return decoded


@dataclass
class Record:
    record_id: int
    text: str
    metadata: Dict[str, Any]
    embedding: List[float]

    def canonical_legacy(self) -> str:
        """Formato historico, exclusivamente para verificar migraciones."""
        return f"{self.record_id}|{self.text}|{sorted(self.metadata.items())}|{','.join(f'{x:.6f}' for x in self.embedding)}"

    def canonical(self) -> str:
        """Formato v2: JSON no ambiguo, claves ordenadas y floats sin redondeo."""
        payload = {
            "record_id": self.record_id,
            "text": self.text,
            "metadata": normalize_metadata(self.metadata),
            "embedding_hex": [float(x).hex() for x in self.embedding],
        }
        return "svdb-record-v2:" + json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Record":
        return cls(
            record_id=int(data["record_id"]),
            text=str(data["text"]),
            metadata=dict(data.get("metadata", {})),
            embedding=[float(x) for x in data.get("embedding", [])],
        )

class RecordStore:
    def __init__(self):
        self._records: Dict[int, Record] = {}

    def insert(self, record: Record) -> None:
        self._records[record.record_id] = record

    def delete(self, record_id: int) -> bool:
        return self._records.pop(record_id, None) is not None

    def get(self, record_id: int) -> Optional[Record]:
        return self._records.get(record_id)

    def all(self) -> List[Record]:
        return [self._records[k] for k in sorted(self._records)]

    def to_list(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.all()]

    def __len__(self) -> int:
        return len(self._records)
