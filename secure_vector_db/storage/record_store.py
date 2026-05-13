from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

@dataclass
class Record:
    record_id: int
    text: str
    metadata: Dict[str, Any]
    embedding: List[float]

    def canonical(self) -> str:
        return f"{self.record_id}|{self.text}|{sorted(self.metadata.items())}|{','.join(f'{x:.6f}' for x in self.embedding)}"

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
