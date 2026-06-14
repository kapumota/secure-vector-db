from __future__ import annotations

import pytest
from fastapi import HTTPException

from secure_vector_db.api.auth import ApiKeyAuthProvider, DisabledAuthProvider
from secure_vector_db.api.auth_scopes import (
    ADMIN_SCOPE,
    READ_SCOPE,
    WRITE_SCOPE,
    AuthenticatedPrincipal,
    authenticate_with_scope,
    parse_scopes,
    require_admin_scope,
    require_auth_scope,
    require_read_scope,
    require_write_scope,
    scope_allows,
    scope_for_endpoint,
)


def test_parse_scopes_accepts_known_scopes() -> None:
    scopes = parse_scopes("read, write, admin")

    assert scopes == frozenset({"read", "write", "admin"})


def test_parse_scopes_rejects_unknown_scope() -> None:
    with pytest.raises(ValueError, match="scopes no soportados"):
        parse_scopes("read,unknown")


def test_scope_allows_admin_for_all_scopes() -> None:
    granted = frozenset({ADMIN_SCOPE})

    assert scope_allows(granted, READ_SCOPE) is True
    assert scope_allows(granted, WRITE_SCOPE) is True
    assert scope_allows(granted, ADMIN_SCOPE) is True


def test_scope_allows_exact_scope() -> None:
    assert scope_allows(frozenset({READ_SCOPE}), READ_SCOPE) is True
    assert scope_allows(frozenset({READ_SCOPE}), WRITE_SCOPE) is False


def test_authenticated_principal_has_scope() -> None:
    principal = AuthenticatedPrincipal(
        name="cliente",
        provider="api_key",
        scopes=frozenset({READ_SCOPE}),
    )

    assert principal.has_scope(READ_SCOPE) is True
    assert principal.has_scope(WRITE_SCOPE) is False


def test_authenticate_with_scope_accepts_valid_key_and_scope() -> None:
    provider = ApiKeyAuthProvider({"secreta"})

    principal = authenticate_with_scope(
        headers={"X-API-Key": "secreta"},
        required_scope=READ_SCOPE,
        provider=provider,
        scopes=frozenset({READ_SCOPE}),
    )

    assert principal.name == "api-key-client"
    assert principal.has_scope(READ_SCOPE) is True


def test_authenticate_with_scope_rejects_invalid_key() -> None:
    provider = ApiKeyAuthProvider({"secreta"})

    with pytest.raises(HTTPException) as exc:
        authenticate_with_scope(
            headers={"X-API-Key": "incorrecta"},
            required_scope=READ_SCOPE,
            provider=provider,
            scopes=frozenset({READ_SCOPE}),
        )

    assert exc.value.status_code == 401


def test_authenticate_with_scope_rejects_missing_scope() -> None:
    provider = ApiKeyAuthProvider({"secreta"})

    with pytest.raises(HTTPException) as exc:
        authenticate_with_scope(
            headers={"X-API-Key": "secreta"},
            required_scope=WRITE_SCOPE,
            provider=provider,
            scopes=frozenset({READ_SCOPE}),
        )

    assert exc.value.status_code == 403


def test_disabled_provider_can_be_scoped_for_tests() -> None:
    principal = authenticate_with_scope(
        headers={},
        required_scope=READ_SCOPE,
        provider=DisabledAuthProvider(),
        scopes=frozenset({READ_SCOPE}),
    )

    assert principal.provider == "disabled"


def test_require_auth_scope_rejects_unknown_scope() -> None:
    with pytest.raises(ValueError, match="scope no soportado"):
        require_auth_scope("unknown")


def test_scope_dependencies_are_created() -> None:
    assert require_read_scope is not None
    assert require_write_scope is not None
    assert require_admin_scope is not None


def test_scope_for_endpoint_maps_write_and_admin() -> None:
    assert scope_for_endpoint("POST", "/records") == WRITE_SCOPE
    assert scope_for_endpoint("POST", "/indexes/learned/retrain") == ADMIN_SCOPE
    assert scope_for_endpoint("GET", "/records/{record_id}") == READ_SCOPE
