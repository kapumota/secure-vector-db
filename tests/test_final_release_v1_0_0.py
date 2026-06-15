from __future__ import annotations

from pathlib import Path

from scripts.version_check import build_version_check, expected_release_tag, is_semantic_version


ROOT = Path(__file__).resolve().parents[1]


def test_final_release_readme_avoids_fragile_dynamic_badges() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "github/v/release" not in readme
    assert "github/license" not in readme
    assert "lanzamiento-v1.0.0" in readme
    assert "licencia-" in readme
    assert "coverage-80%2B" in readme
    assert "supply_chain-0_vulnerabilidades" in readme
    assert "docker_smoke-passing" in readme
    assert "api-estable" in readme


def test_final_release_version_files_are_consistent() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert 'version = "1.0.0"' in pyproject
    assert version_file == "1.0.0"
    assert "Fase 18.0" in changelog


def test_final_release_readme_badges_and_language() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "software base inicial" not in readme
    assert "producto versionado estable inicial" in readme
    assert "badges-release-start" in readme
    assert "badges-release-end" in readme
    assert "actions/workflows/ci.yml/badge.svg" in readme
    assert "actions/workflows/security-baseline.yml/badge.svg" in readme
    assert "final-release-check" in readme
    assert "v1.0.0" in readme


def test_final_release_docs_and_targets_exist() -> None:
    release_doc = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    versioning = (ROOT / "docs" / "VERSIONING.md").read_text(encoding="utf-8")

    assert "Release final v1.0.0" in release_doc
    assert "badges-release-start" in readme
    assert "badges-release-end" in readme
    assert "final-release-check" in makefile
    assert "final-release-strict" in makefile
    assert "v1.0.0" in versioning


def test_final_release_version_check_status() -> None:
    result = build_version_check(ROOT)

    assert is_semantic_version("1.0.0") is True
    assert expected_release_tag("1.0.0") == "v1.0.0"
    assert result.package_version == "1.0.0"
    assert result.expected_tag == "v1.0.0"
    assert result.status == "passed"


def test_release_evidence_knows_final_release() -> None:
    script = (ROOT / "scripts" / "release_evidence.py").read_text(encoding="utf-8")

    assert "check_final_release_readiness" in script
    assert "final-release" in script
