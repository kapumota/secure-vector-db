#!/usr/bin/env python3
"""Auditoria local de baseline de seguridad."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, name: str, detail: str, failures: list[dict[str, str]]) -> None:
    # Registra una falla de auditoria si la condicion no se cumple.
    if not condition:
        failures.append({"check": name, "detail": detail})


def read(path: str) -> str:
    # Lee un archivo del proyecto como texto UTF-8.
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    # Ejecuta verificaciones locales de release security baseline.
    failures: list[dict[str, str]] = []

    dockerfile = read("Dockerfile")
    security_baseline = read("docs/SECURITY_BASELINE.md")
    deployment_security = read("docs/DEPLOYMENT_SECURITY.md")
    api_contract = read("docs/API_CONTRACT.md")
    gitignore = read(".gitignore") if (ROOT / ".gitignore").exists() else ""

    check(
        bool(re.search(r"(?m)^USER\s+(?!root\b).+", dockerfile)),
        "docker_non_root",
        "Dockerfile debe declarar un usuario no root.",
        failures,
    )
    check(
        "X-API-Key" in api_contract,
        "api_key_contract",
        "El contrato de API debe mencionar X-API-Key.",
        failures,
    )
    check(
        "rate limiting actual es en memoria" in security_baseline,
        "memory_rate_limit_documented",
        "La limitacion de rate limiting en memoria debe estar documentada.",
        failures,
    )
    check(
        "SQLite sigue siendo el backend persistente principal" in security_baseline,
        "sqlite_limit_documented",
        "La limitacion de SQLite debe estar documentada.",
        failures,
    )
    check(
        "JWT" in deployment_security or "OAuth2" in deployment_security,
        "future_auth_documented",
        "El despliegue debe mencionar ruta futura hacia JWT u OAuth2.",
        failures,
    )
    check(
        ".env" in gitignore or "*.env" in gitignore,
        "env_ignored",
        ".gitignore debe cubrir archivos de entorno locales.",
        failures,
    )

    result = {
        "status": "failed" if failures else "passed",
        "checks": 6,
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
