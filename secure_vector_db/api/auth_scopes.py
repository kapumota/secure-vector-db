"""Scopes basicos para autenticacion de API."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from fastapi import Header, HTTPException

from secure_vector_db.api.auth import (
    DEFAULT_DEV_API_KEY,
    ApiKeyAuthProvider,
    AuthDecision,
    AuthProvider,
    DisabledAuthProvider,
    parse_api_keys,
)

READ_SCOPE = "read"
WRITE_SCOPE = "write"
ADMIN_SCOPE = "admin"

KNOWN_SCOPES = frozenset({READ_SCOPE, WRITE_SCOPE, ADMIN_SCOPE})
DEFAULT_API_KEY_SCOPES = frozenset({READ_SCOPE, WRITE_SCOPE, ADMIN_SCOPE})


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Principal autenticado con scopes basicos."""

    name: str
    provider: str
    scopes: frozenset[str] = field(default_factory=frozenset)

    def has_scope(self, required_scope: str) -> bool:
        """Indica si el principal puede usar un scope."""
        return scope_allows(self.scopes, required_scope)


def normalize_scope(scope: str) -> str:
    """Normaliza un scope de autenticacion."""
    return scope.strip().lower()


def parse_scopes(raw_value: str) -> frozenset[str]:
    """Convierte una lista separada por comas en scopes validos."""
    scopes = {normalize_scope(item) for item in raw_value.split(",") if item.strip()}
    unknown = scopes - KNOWN_SCOPES
    if unknown:
        raise ValueError(f"scopes no soportados: {', '.join(sorted(unknown))}")
    return frozenset(scopes)


def scope_allows(granted_scopes: frozenset[str] | set[str], required_scope: str) -> bool:
    """Evalua si un conjunto de scopes permite una operacion."""
    normalized = normalize_scope(required_scope)
    if normalized not in KNOWN_SCOPES:
        raise ValueError(f"scope no soportado: {required_scope}")
    return ADMIN_SCOPE in granted_scopes or normalized in granted_scopes


def _compatible_api_keys() -> list[str]:
    """Construye lista de claves compatibles con el servidor actual."""
    raw_keys = os.environ.get("SECURE_VECTOR_DB_API_KEYS", "")
    single_key = os.environ.get("SECURE_VECTOR_DB_API_KEY", "")
    keys = parse_api_keys(raw_keys)
    if single_key.strip():
        keys.append(single_key.strip())
    if DEFAULT_DEV_API_KEY not in keys:
        keys.append(DEFAULT_DEV_API_KEY)
    return keys


def _scopes_from_env() -> frozenset[str]:
    """Lee scopes por defecto desde variables de entorno."""
    raw_scopes = os.environ.get("SECURE_VECTOR_DB_AUTH_SCOPES", "")
    if not raw_scopes.strip():
        return DEFAULT_API_KEY_SCOPES
    return parse_scopes(raw_scopes)


def build_scoped_auth_provider() -> AuthProvider:
    """Construye proveedor compatible para dependencias con scopes."""
    backend = os.environ.get("SECURE_VECTOR_DB_AUTH_BACKEND", "api_key").strip().lower()
    if backend == "disabled":
        return DisabledAuthProvider()
    if backend == "api_key":
        return ApiKeyAuthProvider(_compatible_api_keys())
    raise ValueError(f"backend de autenticacion no soportado: {backend}")


def principal_from_decision(
    decision: AuthDecision,
    scopes: frozenset[str] | None = None,
) -> AuthenticatedPrincipal:
    """Construye un principal autenticado desde una decision."""
    granted_scopes = _scopes_from_env() if scopes is None else scopes
    return AuthenticatedPrincipal(
        name=decision.principal,
        provider=decision.provider,
        scopes=frozenset(granted_scopes),
    )


def authenticate_with_scope(
    headers: Mapping[str, str],
    required_scope: str,
    provider: AuthProvider | None = None,
    scopes: frozenset[str] | None = None,
) -> AuthenticatedPrincipal:
    """Autentica y valida scope requerido."""
    auth_provider = build_scoped_auth_provider() if provider is None else provider
    decision = auth_provider.authenticate(headers)

    if not decision.allowed:
        raise HTTPException(status_code=decision.status_code, detail=decision.reason)

    principal = principal_from_decision(decision, scopes=scopes)
    if not principal.has_scope(required_scope):
        raise HTTPException(status_code=403, detail="scope insuficiente")

    return principal


def require_auth_scope(required_scope: str) -> Callable[[str | None], AuthenticatedPrincipal]:
    """Crea una dependencia FastAPI para un scope requerido."""
    normalized_scope = normalize_scope(required_scope)
    if normalized_scope not in KNOWN_SCOPES:
        raise ValueError(f"scope no soportado: {required_scope}")

    def dependency(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> AuthenticatedPrincipal:
        """Valida API key y scope requerido."""
        return authenticate_with_scope({"X-API-Key": x_api_key or ""}, normalized_scope)

    return dependency


require_read_scope = require_auth_scope(READ_SCOPE)
require_write_scope = require_auth_scope(WRITE_SCOPE)
require_admin_scope = require_auth_scope(ADMIN_SCOPE)


ENDPOINT_SCOPE_MAP = {
    "GET /records/{record_id}": READ_SCOPE,
    "GET /search": READ_SCOPE,
    "GET /explain/records/{record_id}": READ_SCOPE,
    "GET /explain/range": READ_SCOPE,
    "GET /indexes/learned/health": READ_SCOPE,
    "GET /persistence/health": READ_SCOPE,
    "POST /records": WRITE_SCOPE,
    "DELETE /records/{record_id}": WRITE_SCOPE,
    "POST /indexes/learned/retrain": ADMIN_SCOPE,
}


def scope_for_endpoint(method: str, path: str) -> str:
    """Devuelve scope sugerido para un endpoint."""
    key = f"{method.upper()} {path}"
    return ENDPOINT_SCOPE_MAP.get(key, READ_SCOPE)
