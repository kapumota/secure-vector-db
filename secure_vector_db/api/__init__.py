"""Componentes HTTP de SecureVectorDB."""


from secure_vector_db.api.auth import (
    DEFAULT_DEV_API_KEY,
    ApiKeyAuthProvider,
    AuthDecision,
    AuthProvider,
    DisabledAuthProvider,
    auth_provider_info,
    build_auth_provider_from_env,
    require_api_key,
)

__all__ = [
    "DEFAULT_DEV_API_KEY",
    "ApiKeyAuthProvider",
    "AuthDecision",
    "AuthProvider",
    "DisabledAuthProvider",
    "auth_provider_info",
    "build_auth_provider_from_env",
    "require_api_key",
]



from secure_vector_db.api.auth_scopes import (
    ADMIN_SCOPE as ADMIN_SCOPE,
    READ_SCOPE as READ_SCOPE,
    WRITE_SCOPE as WRITE_SCOPE,
    AuthenticatedPrincipal as AuthenticatedPrincipal,
    authenticate_with_scope as authenticate_with_scope,
    require_admin_scope as require_admin_scope,
    require_auth_scope as require_auth_scope,
    require_read_scope as require_read_scope,
    require_write_scope as require_write_scope,
    scope_for_endpoint as scope_for_endpoint,
)

_AUTH_SCOPE_EXPORTS = [
    "ADMIN_SCOPE",
    "READ_SCOPE",
    "WRITE_SCOPE",
    "AuthenticatedPrincipal",
    "authenticate_with_scope",
    "require_admin_scope",
    "require_auth_scope",
    "require_read_scope",
    "require_write_scope",
    "scope_for_endpoint",
]

try:
    __all__.extend(_AUTH_SCOPE_EXPORTS)
except NameError:
    __all__ = _AUTH_SCOPE_EXPORTS
