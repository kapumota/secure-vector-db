"""Proveedores de autenticacion para la API."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable
from fastapi import Header, HTTPException


@dataclass(frozen=True)
class AuthDecision:
    """Resultado de una evaluacion de autenticacion."""

    allowed: bool
    principal: str
    reason: str
    status_code: int
    provider: str
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def allow(cls, principal: str, provider: str, reason: str = "autenticacion aceptada") -> "AuthDecision":
        """Crea una decision permitida."""
        return cls(
            allowed=True,
            principal=principal,
            reason=reason,
            status_code=200,
            provider=provider,
        )

    @classmethod
    def deny(
        cls,
        provider: str,
        reason: str = "autenticacion rechazada",
        status_code: int = 401,
    ) -> "AuthDecision":
        """Crea una decision rechazada."""
        return cls(
            allowed=False,
            principal="anonymous",
            reason=reason,
            status_code=status_code,
            provider=provider,
        )


@runtime_checkable
class AuthProvider(Protocol):
    """Contrato comun para proveedores de autenticacion."""

    name: str

    def authenticate(self, headers: Mapping[str, str]) -> AuthDecision:
        """Evalua autenticacion a partir de headers HTTP."""


def extract_header(headers: Mapping[str, str], header_name: str) -> str:
    """Extrae un header de forma tolerante a mayusculas y minusculas."""
    expected = header_name.lower()
    for key, value in headers.items():
        if key.lower() == expected:
            return value
    return ""


class ApiKeyAuthProvider:
    """Proveedor compatible con autenticacion por X-API-Key."""

    name = "api_key"

    def __init__(
        self,
        valid_api_keys: set[str] | list[str] | tuple[str, ...],
        header_name: str = "X-API-Key",
        principal: str = "api-key-client",
    ) -> None:
        keys = {key.strip() for key in valid_api_keys if key.strip()}
        if not keys:
            raise ValueError("se requiere al menos una API key valida")
        self.valid_api_keys = keys
        self.header_name = header_name
        self.principal = principal

    def authenticate(self, headers: Mapping[str, str]) -> AuthDecision:
        """Valida el header X-API-Key."""
        api_key = extract_header(headers, self.header_name)
        if not api_key:
            return AuthDecision.deny(
                provider=self.name,
                reason="API key requerida",
                status_code=401,
            )
        if api_key not in self.valid_api_keys:
            return AuthDecision.deny(
                provider=self.name,
                reason="API key invalida",
                status_code=401,
            )
        return AuthDecision.allow(
            principal=self.principal,
            provider=self.name,
            reason="API key aceptada",
        )


class DisabledAuthProvider:
    """Proveedor desactivado para pruebas controladas."""

    name = "disabled"

    def authenticate(self, headers: Mapping[str, str]) -> AuthDecision:
        """Permite cualquier solicitud."""
        return AuthDecision.allow(
            principal="disabled-auth-client",
            provider=self.name,
            reason="autenticacion desactivada",
        )


def parse_api_keys(raw_value: str) -> list[str]:
    """Convierte una lista separada por comas en API keys limpias."""
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def build_auth_provider_from_env(env: Mapping[str, str] | None = None) -> AuthProvider:
    """Construye un proveedor de autenticacion desde variables de entorno."""
    source = os.environ if env is None else env
    backend = source.get("SECURE_VECTOR_DB_AUTH_BACKEND", "api_key").strip().lower()

    if backend == "disabled":
        return DisabledAuthProvider()

    if backend == "api_key":
        raw_keys = source.get("SECURE_VECTOR_DB_API_KEYS") or source.get("SECURE_VECTOR_DB_API_KEY", "")
        keys = parse_api_keys(raw_keys)
        if not keys:
            raise RuntimeError("SECURE_VECTOR_DB_API_KEY debe definirse para AuthProvider api_key")
        return ApiKeyAuthProvider(keys)

    raise ValueError(f"backend de autenticacion no soportado: {backend}")


def auth_provider_info(provider: AuthProvider) -> dict[str, str | bool]:
    """Devuelve informacion segura del proveedor de autenticacion."""
    return {
        "backend": provider.name,
        "status": "active",
        "supports_rotation": provider.name == "api_key",
    }

DEFAULT_DEV_API_KEY = "secure-vector-db-dev-key"


def _compatible_api_keys() -> list[str]:
    """Construye lista de API keys compatibles con el servidor actual."""
    raw_keys = os.environ.get("SECURE_VECTOR_DB_API_KEYS", "")
    single_key = os.environ.get("SECURE_VECTOR_DB_API_KEY", "")
    keys = parse_api_keys(raw_keys)
    if single_key.strip():
        keys.append(single_key.strip())
    if DEFAULT_DEV_API_KEY not in keys:
        keys.append(DEFAULT_DEV_API_KEY)
    return keys


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    """Dependencia FastAPI compatible para validar X-API-Key."""
    provider = ApiKeyAuthProvider(_compatible_api_keys())
    decision = provider.authenticate({"X-API-Key": x_api_key or ""})

    if not decision.allowed:
        raise HTTPException(status_code=decision.status_code, detail=decision.reason)

    return decision.principal
