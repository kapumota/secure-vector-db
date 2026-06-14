from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_auth_doc_mentions_provider_contracts() -> None:
    text = (ROOT / "docs" / "AUTH.md").read_text(encoding="utf-8")

    assert "AuthProvider" in text
    assert "AuthDecision" in text
    assert "ApiKeyAuthProvider" in text
    assert "DisabledAuthProvider" in text


def test_auth_doc_mentions_current_header_and_future_path() -> None:
    text = (ROOT / "docs" / "AUTH.md").read_text(encoding="utf-8")

    assert "X-API-Key" in text
    assert "Fase 12.1" in text
    assert "Fase 12.2" in text


def test_security_baseline_mentions_auth_provider_layer() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "Auth provider layer" in text
    assert "ApiKeyAuthProvider" in text


def test_api_contract_mentions_auth_provider_layer() -> None:
    text = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")

    assert "AuthProvider" in text
    assert "X-API-Key" in text
