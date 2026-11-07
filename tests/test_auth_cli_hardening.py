"""Regresiones de autenticación y ejecución CLI."""

import subprocess
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from secure_vector_db.api.auth import DEFAULT_DEV_API_KEY, require_api_key
from secure_vector_db.api.server import app


def test_configured_key_excludes_development_key(monkeypatch):
    monkeypatch.setenv("SECURE_VECTOR_DB_API_KEY", "clave-configurada")
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEYS", raising=False)

    assert require_api_key("clave-configurada") == "api-key-client"

    with pytest.raises(HTTPException) as exc:
        require_api_key(DEFAULT_DEV_API_KEY)

    assert exc.value.status_code == 401


def test_missing_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEY", raising=False)
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEYS", raising=False)
    monkeypatch.setenv("SECURE_VECTOR_DB_ALLOW_DEV_API_KEY", "false")

    with pytest.raises(HTTPException) as exc:
        require_api_key(DEFAULT_DEV_API_KEY)

    assert exc.value.status_code == 401


def test_http_api_rejects_default_key_when_configured(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SECURE_VECTOR_DB_API_KEY", "clave-configurada")
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEYS", raising=False)
    monkeypatch.setenv(
        "SECURE_VECTOR_DB_PATH", str(tmp_path / "api.sqlite")
    )

    with TestClient(app) as client:
        valid = client.get(
            "/verify",
            headers={"X-API-Key": "clave-configurada"},
        )
        invalid = client.get(
            "/verify",
            headers={"X-API-Key": DEFAULT_DEV_API_KEY},
        )

    assert valid.status_code == 200
    assert invalid.status_code == 401


def test_cli_module_runs_demo():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "secure_vector_db.cli",
            "--index",
            "kd_tree",
            "--embedding",
            "hash",
            "demo",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "SecureVectorDB demo" in result.stdout
    assert "Verificacion: True" in result.stdout
