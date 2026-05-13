from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, status

API_KEY_ENV = "SECURE_VECTOR_DB_API_KEY"
DEFAULT_DEV_API_KEY = "dev-secret-key"


def get_api_key() -> str:
    """Devuelve la clave API configurada.Para demostraciones locales, se proporciona 
    una clave de desarrollo determinista. En Docker o producción, establece
    SECURE_VECTOR_DB_API_KEY en un valor aleatorio seguro..
    """
    return os.environ.get(API_KEY_ENV, DEFAULT_DEV_API_KEY)


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = get_api_key()
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida o ausente. Envíe el header X-API-Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
