from __future__ import annotations

from pathlib import Path

from scripts.version_check import (
    build_version_check,
    expected_release_tag,
    is_semantic_version,
)


ROOT = Path(__file__).resolve().parents[1]


def test_readme_uses_versioned_product_language() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "software base inicial" not in text
    assert "producto versionado inicial" in text
    assert "release-candidate-check" in text


def test_release_candidate_docs_and_targets_exist() -> None:
    release_doc = (ROOT / "docs" / "RELEASE_CANDIDATE.md").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    versioning = (ROOT / "docs" / "VERSIONING.md").read_text(encoding="utf-8")

    assert "Fase 17.0" in release_doc
    assert "v1.0.0-rc1" in release_doc
    assert "release-candidate-check" in makefile
    assert "release-candidate-strict" in makefile
    assert "v1.0.0-rc1" in versioning


def test_release_candidate_version_files_are_consistent() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert 'version = "1.0.0rc1"' in pyproject
    assert version_file == "1.0.0rc1"
    assert "Fase 17.0" in changelog


def test_version_check_accepts_rc_version_and_tag() -> None:
    assert is_semantic_version("1.0.0rc1") is True
    assert is_semantic_version("1.0.0-rc1") is True
    assert expected_release_tag("1.0.0rc1") == "v1.0.0-rc1"
    assert expected_release_tag("1.0.0-rc1") == "v1.0.0-rc1"


def test_build_version_check_for_release_candidate() -> None:
    result = build_version_check(ROOT)

    assert result.package_version == "1.0.0rc1"
    assert result.expected_tag == "v1.0.0-rc1"
    assert result.status == "passed"
