"""Configuracion de pruebas de SecureVectorDB."""

import pytest


@pytest.fixture
def enable_test_api_key(monkeypatch):
    """Habilita una clave de desarrollo solo para la prueba solicitante."""
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEY", raising=False)
    monkeypatch.delenv("SECURE_VECTOR_DB_API_KEYS", raising=False)
    monkeypatch.setenv(
        "SECURE_VECTOR_DB_ALLOW_DEV_API_KEY", "true"
    )
