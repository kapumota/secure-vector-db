from __future__ import annotations

from pathlib import Path

from scripts.version_check import expected_release_tag, is_semantic_version


ROOT = Path(__file__).resolve().parents[1]


def test_readme_uses_versioned_product_language() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "software base inicial" not in text
    assert "producto versionado" in text
    assert "release-candidate-check" in text


def test_release_candidate_docs_and_targets_remain_documented() -> None:
    release_doc = (ROOT / "docs" / "RELEASE_CANDIDATE.md").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    versioning = (ROOT / "docs" / "VERSIONING.md").read_text(encoding="utf-8")

    assert "Fase 17.0" in release_doc
    assert "v1.0.0-rc1" in release_doc
    assert "release-candidate-check" in makefile
    assert "release-candidate-strict" in makefile
    assert "v1.0.0-rc1" in versioning


def test_release_candidate_version_format_remains_valid() -> None:
    assert is_semantic_version("1.0.0rc1") is True
    assert is_semantic_version("1.0.0-rc1") is True
    assert expected_release_tag("1.0.0rc1") == "v1.0.0-rc1"
    assert expected_release_tag("1.0.0-rc1") == "v1.0.0-rc1"
