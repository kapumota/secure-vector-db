from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_storage_documentation_mentions_current_and_future_backends() -> None:
    text = (ROOT / "docs" / "STORAGE.md").read_text(encoding="utf-8")

    assert "Backend persistente estable: SQLite" in text
    assert "Backend PostgreSQL pgvector: planificado" in text
    assert "PersistentRecordStore" in text
    assert "VolatileRecordStore" in text


def test_security_baseline_links_storage_abstraction() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "storage abstraction layer" in text
    assert "PostgresRecordStore experimental" in text
