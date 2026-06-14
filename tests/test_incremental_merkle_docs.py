from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_merkle_incremental_doc_mentions_phase_scope() -> None:
    text = (ROOT / "docs" / "MERKLE_INCREMENTAL.md").read_text(encoding="utf-8")

    assert "Fase 13.0" in text
    assert "IncrementalMerkleTree" in text
    assert "Fase 13.1" in text


def test_merkle_incremental_doc_mentions_expected_modes() -> None:
    text = (ROOT / "docs" / "MERKLE_INCREMENTAL.md").read_text(encoding="utf-8")

    assert "path" in text
    assert "rebuild" in text
    assert "noop" in text


def test_readme_mentions_incremental_merkle() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "MERKLE_INCREMENTAL.md" in text
    assert "Merkle incremental" in text


def test_security_baseline_mentions_incremental_merkle() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "Merkle incremental" in text
    assert "Fase 13.0" in text
