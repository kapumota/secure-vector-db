from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_supply_chain_doc_mentions_phase_and_targets() -> None:
    text = (ROOT / "docs" / "SUPPLY_CHAIN_SECURITY.md").read_text(encoding="utf-8")

    assert "Fase 14.1" in text
    assert "make supply-chain-check" in text
    assert "pip-audit" in text


def test_release_evidence_doc_mentions_supply_chain() -> None:
    text = (ROOT / "docs" / "RELEASE_EVIDENCE.md").read_text(encoding="utf-8")

    assert "SBOM" in text
    assert "vulnerability scan" in text
    assert "Fase 14.1" in text


def test_makefile_mentions_supply_chain_targets() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "supply-chain-check" in text
    assert "supply-chain-strict" in text
    assert "scripts/supply_chain_security.py" in text


def test_security_baseline_mentions_supply_chain() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "supply chain" in text
    assert "Fase 14.1" in text
