from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_jwt_doc_mentions_experimental_backend() -> None:
    text = (ROOT / "docs" / "AUTH_JWT_EXPERIMENTAL.md").read_text(encoding="utf-8")

    assert "JwtAuthProvider" in text
    assert "experimental" in text
    assert "Authorization: Bearer" in text
    assert "HS256" in text


def test_auth_doc_mentions_jwt_experimental_doc() -> None:
    text = (ROOT / "docs" / "AUTH.md").read_text(encoding="utf-8")

    assert "Fase 12.2" in text
    assert "AUTH_JWT_EXPERIMENTAL.md" in text


def test_api_contract_mentions_jwt_experimental() -> None:
    text = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")

    assert "JWT experimental" in text
    assert "X-API-Key" in text


def test_security_baseline_mentions_jwt_experimental() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "JwtAuthProvider" in text
    assert "experimental" in text
