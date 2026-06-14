from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_merkle_persistence_doc_mentions_recovery() -> None:
    text = (ROOT / "docs" / "MERKLE_PERSISTENCE.md").read_text(encoding="utf-8")

    assert "Fase 13.1" in text
    assert "SQLiteMerkleNodeStore" in text
    assert "recovery" in text


def test_merkle_incremental_doc_links_persistence_phase() -> None:
    text = (ROOT / "docs" / "MERKLE_INCREMENTAL.md").read_text(encoding="utf-8")

    assert "MERKLE_PERSISTENCE.md" in text
    assert "Fase 13.1" in text


def test_security_baseline_mentions_merkle_persistence() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "Persistencia y recovery de Merkle incremental" in text
    assert "Fase 13.1" in text


def test_api_contract_mentions_no_public_merkle_api_yet() -> None:
    text = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")

    assert "MERKLE_PERSISTENCE.md" in text
    assert "no cambia endpoints" in text
