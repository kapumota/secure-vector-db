from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_versioning_doc_mentions_phase_and_targets() -> None:
    text = (ROOT / "docs" / "VERSIONING.md").read_text(encoding="utf-8")

    assert "Fase 16.0" in text
    assert "make version-check" in text
    assert "make version-strict" in text


def test_api_contract_mentions_stable_and_experimental() -> None:
    text = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")

    assert "Fase 16.0" in text
    assert "estable" in text
    assert "experimental" in text
    assert "versionado" in text


def test_changelog_mentions_phase_16() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "Fase 16.0" in text


def test_release_evidence_mentions_version_check() -> None:
    text = (ROOT / "docs" / "RELEASE_EVIDENCE.md").read_text(encoding="utf-8")

    assert "version-check" in text
    assert "Fase 16.0" in text


def test_makefile_mentions_version_targets() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "version-check" in text
    assert "version-strict" in text
    assert "scripts/version_check.py" in text
