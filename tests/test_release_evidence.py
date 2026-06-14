from __future__ import annotations

import json
from pathlib import Path

from scripts.release_evidence import (
    build_release_manifest,
    detect_package_version,
    run_release_evidence,
)


def test_detect_package_version_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "secure-vector-db"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )

    assert detect_package_version(tmp_path) == "1.2.3"


def test_build_release_manifest_reports_required_checks() -> None:
    root = Path(__file__).resolve().parents[1]

    manifest = build_release_manifest(root)
    checks = {check.name for check in manifest.checks}

    assert "required-docs" in checks
    assert "forbidden-artifacts" in checks
    assert "env-files" in checks
    assert "merkle-evidence-line" in checks


def test_run_release_evidence_writes_manifest(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_path = tmp_path / "release" / "manifest.json"

    exit_code = run_release_evidence(
        [
            "--root",
            str(project_root),
            "--output",
            str(output_path),
            "--check",
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["checks"]
    assert payload["package_version"]
