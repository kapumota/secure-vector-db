from __future__ import annotations

import time

from secure_vector_db.api.auth import AuthProvider, build_auth_provider_from_env
from secure_vector_db.api.auth_jwt import (
    JwtAuthProvider,
    build_jwt_auth_provider_from_env,
    create_hs256_jwt,
    decode_hs256_jwt,
    jwt_auth_provider_info,
    jwt_scopes_from_payload,
    parse_bearer_token,
)


def test_parse_bearer_token_accepts_authorization_header() -> None:
    token = parse_bearer_token({"Authorization": "Bearer abc.def.ghi"})

    assert token == "abc.def.ghi"


def test_jwt_provider_accepts_valid_token() -> None:
    secret = "clave-jwt"
    token = create_hs256_jwt(
        {
            "sub": "cliente",
            "scope": "read write",
            "exp": int(time.time()) + 60,
        },
        secret,
    )
    provider = JwtAuthProvider(secret=secret)

    decision = provider.authenticate({"Authorization": f"Bearer {token}"})

    assert isinstance(provider, AuthProvider)
    assert decision.allowed is True
    assert decision.principal == "cliente"
    assert decision.metadata["scopes"] == "read,write"


def test_jwt_provider_rejects_invalid_signature() -> None:
    token = create_hs256_jwt({"sub": "cliente"}, "clave-correcta")
    provider = JwtAuthProvider(secret="clave-incorrecta")

    decision = provider.authenticate({"Authorization": f"Bearer {token}"})

    assert decision.allowed is False
    assert decision.status_code == 401
    assert "firma JWT invalida" in decision.reason


def test_jwt_provider_rejects_expired_token() -> None:
    token = create_hs256_jwt({"sub": "cliente", "exp": int(time.time()) - 60}, "clave")
    provider = JwtAuthProvider(secret="clave")

    decision = provider.authenticate({"Authorization": f"Bearer {token}"})

    assert decision.allowed is False
    assert "JWT expirado" in decision.reason


def test_decode_hs256_jwt_validates_issuer_and_audience() -> None:
    token = create_hs256_jwt(
        {
            "sub": "cliente",
            "iss": "secure-vector-db",
            "aud": "api",
            "exp": int(time.time()) + 60,
        },
        "clave",
    )

    payload = decode_hs256_jwt(
        token,
        secret="clave",
        issuer="secure-vector-db",
        audience="api",
    )

    assert payload["sub"] == "cliente"


def test_jwt_scopes_from_payload_accepts_list() -> None:
    scopes = jwt_scopes_from_payload({"scopes": ["read", "admin"]})

    assert scopes == frozenset({"read", "admin"})


def test_build_jwt_auth_provider_from_env() -> None:
    provider = build_jwt_auth_provider_from_env(
        {
            "SECURE_VECTOR_DB_JWT_SECRET": "clave",
            "SECURE_VECTOR_DB_JWT_ISSUER": "secure-vector-db",
            "SECURE_VECTOR_DB_JWT_AUDIENCE": "api",
            "SECURE_VECTOR_DB_JWT_LEEWAY_SECONDS": "5",
        }
    )

    info = jwt_auth_provider_info(provider)

    assert info["backend"] == "jwt_experimental"
    assert info["issuer_configured"] is True
    assert info["audience_configured"] is True
    assert info["leeway_seconds"] == 5


def test_build_auth_provider_from_env_supports_jwt_backend() -> None:
    provider = build_auth_provider_from_env(
        {
            "SECURE_VECTOR_DB_AUTH_BACKEND": "jwt",
            "SECURE_VECTOR_DB_JWT_SECRET": "clave",
        }
    )

    assert isinstance(provider, JwtAuthProvider)
