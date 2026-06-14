from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_dockerfile_uses_non_root_user() -> None:
    dockerfile = read("Dockerfile")

    assert re.search(r"(?m)^USER\s+(?!root\b).+", dockerfile)


def test_security_baseline_documents_known_limits() -> None:
    baseline = read("docs/SECURITY_BASELINE.md")

    assert "SQLite sigue siendo el backend persistente principal" in baseline
    assert "rate limiting actual es en memoria" in baseline
    assert "X-API-Key" in baseline
    assert "Merkle root actual" in baseline
    assert "PATCH /records/{record_id}/metadata" in baseline


def test_deployment_security_documents_future_scaling_path() -> None:
    deployment = read("docs/DEPLOYMENT_SECURITY.md")

    assert "usuario no root" in deployment
    assert "Redis" in deployment
    assert "PostgreSQL" in deployment
    assert "JWT" in deployment or "OAuth2" in deployment


def test_security_audit_script_exists() -> None:
    audit_script = read("scripts/security_audit.py")

    assert "docker_non_root" in audit_script
    assert "api_key_contract" in audit_script
    assert "memory_rate_limit_documented" in audit_script


def test_api_contract_keeps_api_key_requirement() -> None:
    api_contract = read("docs/API_CONTRACT.md")

    assert "X-API-Key" in api_contract
