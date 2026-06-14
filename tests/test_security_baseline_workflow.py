from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_security_baseline_workflow_exists() -> None:
    workflow = ROOT / ".github" / "workflows" / "security-baseline.yml"

    assert workflow.exists()
    text = workflow.read_text(encoding="utf-8")
    assert "python scripts/security_audit.py" in text
