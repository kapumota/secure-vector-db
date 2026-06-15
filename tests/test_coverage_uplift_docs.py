from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_coverage_uplift_doc_mentions_release_initial() -> None:
    text = (ROOT / "docs" / "COVERAGE_UPLIFT.md").read_text(encoding="utf-8")

    assert "Fase 16.1" in text
    assert "release inicial" in text
    assert "make coverage-strict" in text


def test_makefile_mentions_release_initial_targets() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "coverage-uplift-check" in text
    assert "release-initial-check" in text
    assert "coverage-strict" in text


def test_release_evidence_mentions_coverage_uplift() -> None:
    text = (ROOT / "docs" / "RELEASE_EVIDENCE.md").read_text(encoding="utf-8")

    assert "Fase 16.1" in text
    assert "COVERAGE_UPLIFT" in text


def test_changelog_mentions_coverage_uplift() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "Fase 16.1" in text
