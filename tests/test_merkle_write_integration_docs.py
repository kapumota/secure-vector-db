from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_merkle_write_doc_mentions_phase_and_env() -> None:
    text = (ROOT / "docs" / "MERKLE_WRITE_INTEGRATION.md").read_text(encoding="utf-8")

    assert "Fase 15.0" in text
    assert "SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION" in text
    assert "insert real cambia root Merkle" in text


def test_database_exposes_merkle_write_methods() -> None:
    text = (ROOT / "secure_vector_db" / "database.py").read_text(encoding="utf-8")

    assert "_apply_merkle_write_insert" in text
    assert "_apply_merkle_write_delete" in text
    assert "verify_merkle_integrity" in text


def test_release_evidence_mentions_merkle_write_integration() -> None:
    text = (ROOT / "docs" / "RELEASE_EVIDENCE.md").read_text(encoding="utf-8")

    assert "Fase 15.0" in text
    assert "MERKLE_WRITE_INTEGRATION" in text


def test_security_baseline_mentions_merkle_write_integration() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "Fase 15.0" in text
    assert "escrituras reales" in text
