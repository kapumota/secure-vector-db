from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_merkle_evidence_doc_mentions_api_and_report() -> None:
    text = (ROOT / "docs" / "MERKLE_EVIDENCE.md").read_text(encoding="utf-8")

    assert "Fase 13.2" in text
    assert "MerkleEvidenceReport" in text
    assert "/merkle/evidence" in text


def test_merkle_persistence_doc_links_evidence_phase() -> None:
    text = (ROOT / "docs" / "MERKLE_PERSISTENCE.md").read_text(encoding="utf-8")

    assert "MERKLE_EVIDENCE.md" in text
    assert "Fase 13.2" in text


def test_api_contract_mentions_merkle_evidence_api() -> None:
    text = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")

    assert "MERKLE_EVIDENCE.md" in text
    assert "/merkle/root" in text
    assert "/merkle/verify" in text


def test_security_baseline_mentions_merkle_evidence() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "Fase 13.2" in text
    assert "evidencia Merkle verificable" in text
