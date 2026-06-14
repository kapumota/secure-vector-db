from __future__ import annotations

import json
from pathlib import Path

from scripts.supply_chain_security import (
    build_cyclonedx_sbom,
    build_skipped_audit_report,
    generate_supply_chain_reports,
    run_supply_chain_security,
)


def test_build_cyclonedx_sbom_has_required_shape() -> None:
    root = Path(__file__).resolve().parents[1]

    sbom = build_cyclonedx_sbom(root)

    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["metadata"]["component"]["name"] == "secure-vector-db"
    assert isinstance(sbom["components"], list)


def test_build_skipped_audit_report_is_explicit() -> None:
    report = build_skipped_audit_report()

    assert report["status"] == "skipped"
    assert report["tool"] == "pip-audit"


def test_generate_supply_chain_reports_with_skip_audit(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    sbom_output = tmp_path / "sbom.json"
    vulnerability_output = tmp_path / "vulnerability-report.json"

    summary = generate_supply_chain_reports(
        root=root,
        sbom_output=sbom_output,
        vulnerability_output=vulnerability_output,
        skip_audit=True,
    )

    assert summary.sbom_status == "passed"
    assert summary.vulnerability_status == "skipped"
    assert sbom_output.exists()
    assert vulnerability_output.exists()


def test_run_supply_chain_security_writes_reports(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    sbom_output = tmp_path / "sbom.json"
    vulnerability_output = tmp_path / "vulnerability-report.json"

    exit_code = run_supply_chain_security(
        [
            "--root",
            str(root),
            "--sbom-output",
            str(sbom_output),
            "--vulnerability-output",
            str(vulnerability_output),
            "--skip-audit",
            "--check",
        ]
    )

    payload = json.loads(sbom_output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["bomFormat"] == "CycloneDX"
    assert vulnerability_output.exists()
