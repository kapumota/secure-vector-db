from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_api_contract_mentions_detected_routes() -> None:
    server_text = (ROOT / "secure_vector_db" / "api" / "server.py").read_text(encoding="utf-8")
    contract_text = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")

    routes = set(re.findall(r"@app\.(?:get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]", server_text))

    required = {
        "/indexes/learned/health",
        "/explain/records/{record_id}",
        "/explain/range",
        "/persistence/health",
    }

    for route in required:
        if route in routes:
            assert route in contract_text


def test_cli_contract_mentions_detected_commands() -> None:
    cli_text = (ROOT / "secure_vector_db" / "cli.py").read_text(encoding="utf-8")
    contract_text = (ROOT / "docs" / "CLI_CONTRACT.md").read_text(encoding="utf-8")

    commands = set(re.findall(r"sub\.add_parser\(\s*['\"]([^'\"]+)['\"]", cli_text))

    required = {
        "index-health",
        "retrain-learned-index",
        "explain-get",
        "explain-range",
        "persistence-health",
    }

    for command in required:
        if command in commands:
            assert command in contract_text


def test_contract_docs_define_stability_policy() -> None:
    api_contract = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")
    cli_contract = (ROOT / "docs" / "CLI_CONTRACT.md").read_text(encoding="utf-8")
    errors_doc = (ROOT / "docs" / "ERRORS.md").read_text(encoding="utf-8")

    assert "estable durante toda la serie 1.x" in api_contract
    assert "estable durante toda la serie 1.x" in cli_contract
    assert "validation_error" in errors_doc
    assert "learned_index_needs_retrain" in errors_doc
