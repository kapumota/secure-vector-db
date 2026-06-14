from __future__ import annotations

import json
from pathlib import Path

from scripts.version_check import (
    build_version_check,
    detect_pyproject_version,
    expected_release_tag,
    run_version_check,
)


def test_detect_pyproject_version(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "secure-vector-db"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )

    assert detect_pyproject_version(tmp_path) == "1.2.3"


def test_expected_release_tag() -> None:
    assert expected_release_tag("1.2.3") == "v1.2.3"


def test_build_version_check_on_project_root() -> None:
    root = Path(__file__).resolve().parents[1]

    result = build_version_check(root)

    assert result.package_version
    assert result.expected_tag.startswith("v")
    assert {check.name for check in result.checks} >= {
        "pyproject-version",
        "git-tag",
        "changelog",
        "api-contract-freeze",
    }


def test_run_version_check_writes_report(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "version-check.json"

    exit_code = run_version_check(
        [
            "--root",
            str(root),
            "--output",
            str(output),
            "--check",
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["package_version"]
