"""Proveedor JWT experimental para autenticacion de API."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Mapping

from secure_vector_db.api.auth import AuthDecision, AuthProvider
from secure_vector_db.api.auth_scopes import parse_scopes


class JwtValidationError(ValueError):
    """Error de validacion de JWT experimental."""


def _b64url_encode(raw: bytes) -> str:
    """Codifica bytes usando base64url sin padding."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    """Decodifica base64url con padding tolerante."""
    padding = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode((raw + padding).encode("ascii"))
    except Exception as exc:
        raise JwtValidationError("segmento base64url invalido") from exc


def parse_bearer_token(headers: Mapping[str, str]) -> str:
    """Extrae token Bearer de headers HTTP."""
    authorization = ""
    for key, value in headers.items():
        if key.lower() == "authorization":
            authorization = value.strip()
            break

    if not authorization:
        raise JwtValidationError("header Authorization requerido")

    prefix = "bearer "
    if not authorization.lower().startswith(prefix):
        raise JwtValidationError("token Bearer requerido")

    token = authorization[len(prefix) :].strip()
    if not token:
        raise JwtValidationError("token Bearer vacio")
    return token


def _json_from_segment(segment: str) -> dict[str, Any]:
    """Convierte un segmento JWT en diccionario JSON."""
    try:
        value = json.loads(_b64url_decode(segment).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise JwtValidationError("segmento JSON invalido") from exc
    if not isinstance(value, dict):
        raise JwtValidationError("segmento JSON debe ser objeto")
    return value


def _sign_hs256(signing_input: str, secret: str) -> str:
    """Firma un bloque JWT con HS256."""
    digest = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(digest)


def decode_hs256_jwt(
    token: str,
    secret: str,
    issuer: str | None = None,
    audience: str | None = None,
    leeway_seconds: int = 0,
    now: float | None = None,
) -> dict[str, Any]:
    """Valida y decodifica un JWT HS256 experimental."""
    if not secret:
        raise JwtValidationError("secreto JWT requerido")

    parts = token.split(".")
    if len(parts) != 3:
        raise JwtValidationError("JWT debe tener tres segmentos")

    header_segment, payload_segment, signature_segment = parts
    header = _json_from_segment(header_segment)
    payload = _json_from_segment(payload_segment)

    if header.get("alg") != "HS256":
        raise JwtValidationError("solo HS256 esta soportado")
    if header.get("typ", "JWT") != "JWT":
        raise JwtValidationError("tipo JWT invalido")

    signing_input = f"{header_segment}.{payload_segment}"
    expected_signature = _sign_hs256(signing_input, secret)
    if not hmac.compare_digest(expected_signature, signature_segment):
        raise JwtValidationError("firma JWT invalida")

    current = time.time() if now is None else now

    exp = payload.get("exp")
    if exp is not None and current > float(exp) + leeway_seconds:
        raise JwtValidationError("JWT expirado")

    nbf = payload.get("nbf")
    if nbf is not None and current + leeway_seconds < float(nbf):
        raise JwtValidationError("JWT aun no es valido")

    if issuer is not None and payload.get("iss") != issuer:
        raise JwtValidationError("issuer JWT invalido")

    if audience is not None:
        token_audience = payload.get("aud")
        if isinstance(token_audience, list):
            valid_audience = audience in token_audience
        else:
            valid_audience = token_audience == audience
        if not valid_audience:
            raise JwtValidationError("audience JWT invalido")

    return payload


def jwt_scopes_from_payload(payload: Mapping[str, Any]) -> frozenset[str]:
    """Extrae scopes desde claims scope o scopes."""
    raw_scopes = payload.get("scope", "")
    if not raw_scopes and "scopes" in payload:
        scopes_value = payload["scopes"]
        if isinstance(scopes_value, list):
            raw_scopes = ",".join(str(item) for item in scopes_value)
        else:
            raw_scopes = str(scopes_value)

    if isinstance(raw_scopes, str):
        normalized = raw_scopes.replace(" ", ",")
        return parse_scopes(normalized) if normalized.strip() else frozenset()

    raise JwtValidationError("claim de scopes invalido")


class JwtAuthProvider:
    """Proveedor JWT experimental basado en HS256."""

    name = "jwt_experimental"

    def __init__(
        self,
        secret: str,
        issuer: str | None = None,
        audience: str | None = None,
        leeway_seconds: int = 0,
    ) -> None:
        if not secret:
            raise ValueError("secreto JWT requerido")
        self.secret = secret
        self.issuer = issuer
        self.audience = audience
        self.leeway_seconds = leeway_seconds

    def authenticate(self, headers: Mapping[str, str]) -> AuthDecision:
        """Valida Authorization Bearer con JWT HS256."""
        try:
            token = parse_bearer_token(headers)
            payload = decode_hs256_jwt(
                token=token,
                secret=self.secret,
                issuer=self.issuer,
                audience=self.audience,
                leeway_seconds=self.leeway_seconds,
            )
            principal = str(payload.get("sub", "jwt-client"))
            scopes = ",".join(sorted(jwt_scopes_from_payload(payload)))
            return AuthDecision(
                allowed=True,
                principal=principal,
                reason="JWT aceptado",
                status_code=200,
                provider=self.name,
                metadata={"scopes": scopes},
            )
        except JwtValidationError as exc:
            return AuthDecision.deny(
                provider=self.name,
                reason=f"JWT invalido: {exc}",
                status_code=401,
            )


def build_jwt_auth_provider_from_env(env: Mapping[str, str] | None = None) -> JwtAuthProvider:
    """Construye JwtAuthProvider desde variables de entorno."""
    source = os.environ if env is None else env
    secret = source.get("SECURE_VECTOR_DB_JWT_SECRET", "")
    issuer = source.get("SECURE_VECTOR_DB_JWT_ISSUER") or None
    audience = source.get("SECURE_VECTOR_DB_JWT_AUDIENCE") or None
    leeway_seconds = int(source.get("SECURE_VECTOR_DB_JWT_LEEWAY_SECONDS", "0"))
    return JwtAuthProvider(
        secret=secret,
        issuer=issuer,
        audience=audience,
        leeway_seconds=leeway_seconds,
    )


def create_hs256_jwt(
    payload: Mapping[str, Any],
    secret: str,
    header: Mapping[str, Any] | None = None,
) -> str:
    """Crea JWT HS256 para pruebas y demos controladas."""
    jwt_header = {"alg": "HS256", "typ": "JWT"}
    if header:
        jwt_header.update(dict(header))

    header_segment = _b64url_encode(
        json.dumps(jwt_header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_segment = _b64url_encode(
        json.dumps(dict(payload), separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}"
    signature = _sign_hs256(signing_input, secret)
    return f"{signing_input}.{signature}"


def jwt_auth_provider_info(provider: JwtAuthProvider) -> dict[str, str | bool | int | None]:
    """Devuelve informacion segura del proveedor JWT."""
    return {
        "backend": provider.name,
        "algorithm": "HS256",
        "issuer_configured": provider.issuer is not None,
        "audience_configured": provider.audience is not None,
        "leeway_seconds": provider.leeway_seconds,
        "status": "experimental",
    }


def ensure_auth_provider_compatible(provider: AuthProvider) -> AuthProvider:
    """Devuelve proveedor para compatibilidad de tipos."""
    return provider
