from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_auth_scopes_doc_mentions_scopes_and_errors() -> None:
    text = (ROOT / "docs" / "AUTH_SCOPES.md").read_text(encoding="utf-8")

    assert "read" in text
    assert "write" in text
    assert "admin" in text
    assert "401" in text
    assert "403" in text


def test_auth_doc_links_scope_phase() -> None:
    text = (ROOT / "docs" / "AUTH.md").read_text(encoding="utf-8")

    assert "Fase 12.1" in text
    assert "AUTH_SCOPES.md" in text


def test_api_contract_mentions_scope_policy() -> None:
    text = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")

    assert "read" in text
    assert "write" in text
    assert "admin" in text
    assert "403" in text


def test_security_baseline_mentions_scope_layer() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "scopes basicos" in text
    assert "Auth middleware" in text
