from __future__ import annotations

import pytest

from secure_vector_db.api.auth import (
    ApiKeyAuthProvider,
    AuthProvider,
    DisabledAuthProvider,
    auth_provider_info,
    build_auth_provider_from_env,
    extract_header,
    parse_api_keys,
)


def test_api_key_provider_accepts_valid_key() -> None:
    provider = ApiKeyAuthProvider({"secreta"})

    decision = provider.authenticate({"X-API-Key": "secreta"})

    assert isinstance(provider, AuthProvider)
    assert decision.allowed is True
    assert decision.principal == "api-key-client"
    assert decision.provider == "api_key"


def test_api_key_provider_rejects_missing_key() -> None:
    provider = ApiKeyAuthProvider({"secreta"})

    decision = provider.authenticate({})

    assert decision.allowed is False
    assert decision.status_code == 401
    assert decision.reason == "API key requerida"


def test_api_key_provider_rejects_invalid_key() -> None:
    provider = ApiKeyAuthProvider({"secreta"})

    decision = provider.authenticate({"X-API-Key": "incorrecta"})

    assert decision.allowed is False
    assert decision.status_code == 401
    assert decision.reason == "API key invalida"


def test_api_key_provider_is_case_insensitive_for_header_name() -> None:
    provider = ApiKeyAuthProvider({"secreta"})

    decision = provider.authenticate({"x-api-key": "secreta"})

    assert decision.allowed is True


def test_disabled_auth_provider_allows_request() -> None:
    provider = DisabledAuthProvider()

    decision = provider.authenticate({})

    assert decision.allowed is True
    assert decision.provider == "disabled"


def test_build_auth_provider_from_env_builds_api_key_backend() -> None:
    provider = build_auth_provider_from_env(
        {
            "SECURE_VECTOR_DB_AUTH_BACKEND": "api_key",
            "SECURE_VECTOR_DB_API_KEY": "secreta",
        }
    )

    decision = provider.authenticate({"X-API-Key": "secreta"})

    assert decision.allowed is True


def test_build_auth_provider_from_env_supports_multiple_keys() -> None:
    provider = build_auth_provider_from_env(
        {
            "SECURE_VECTOR_DB_AUTH_BACKEND": "api_key",
            "SECURE_VECTOR_DB_API_KEYS": "clave-a, clave-b",
        }
    )

    assert provider.authenticate({"X-API-Key": "clave-a"}).allowed is True
    assert provider.authenticate({"X-API-Key": "clave-b"}).allowed is True


def test_build_auth_provider_from_env_requires_key_for_api_key_backend() -> None:
    with pytest.raises(RuntimeError, match="SECURE_VECTOR_DB_API_KEY debe definirse"):
        build_auth_provider_from_env({"SECURE_VECTOR_DB_AUTH_BACKEND": "api_key"})


def test_build_auth_provider_from_env_builds_disabled_backend() -> None:
    provider = build_auth_provider_from_env({"SECURE_VECTOR_DB_AUTH_BACKEND": "disabled"})

    assert isinstance(provider, DisabledAuthProvider)


def test_build_auth_provider_from_env_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="backend de autenticacion no soportado"):
        build_auth_provider_from_env({"SECURE_VECTOR_DB_AUTH_BACKEND": "oauth"})


def test_parse_api_keys_trims_empty_values() -> None:
    assert parse_api_keys(" a, , b ") == ["a", "b"]


def test_extract_header_is_case_insensitive() -> None:
    assert extract_header({"x-api-key": "valor"}, "X-API-Key") == "valor"


def test_auth_provider_info_is_safe() -> None:
    provider = ApiKeyAuthProvider({"secreta"})

    info = auth_provider_info(provider)

    assert info["backend"] == "api_key"
    assert info["supports_rotation"] is True
    assert "secreta" not in str(info)
