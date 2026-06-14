from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_evidence_doc_mentions_make_target() -> None:
    text = (ROOT / "docs" / "RELEASE_EVIDENCE.md").read_text(encoding="utf-8")

    assert "Fase 14.0" in text
    assert "make release-check" in text
    assert "Fase 14.1" in text


def test_makefile_mentions_release_check() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "release-check" in text
    assert "scripts/release_evidence.py" in text


def test_security_baseline_mentions_release_evidence() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "Evidence Pack" in text
    assert "Fase 14.0" in text


def test_readme_mentions_release_evidence() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/RELEASE_EVIDENCE.md" in text
