### JWT experimental

#### Objetivo

La Fase 12.2 agrega `JwtAuthProvider` como proveedor experimental.

El objetivo es preparar autenticacion Bearer con JWT sin reemplazar `ApiKeyAuthProvider` como backend estable.

#### Estado

```text
ApiKeyAuthProvider: estable
JwtAuthProvider: experimental
OAuth2 completo: fuera de esta fase
```

#### Variables de entorno

```text
SECURE_VECTOR_DB_AUTH_BACKEND=jwt
SECURE_VECTOR_DB_JWT_SECRET=clave-local
SECURE_VECTOR_DB_JWT_ISSUER=secure-vector-db
SECURE_VECTOR_DB_JWT_AUDIENCE=api
SECURE_VECTOR_DB_JWT_LEEWAY_SECONDS=5
```

#### Header esperado

```text
Authorization: Bearer <token>
```

#### Algoritmo soportado

```text
HS256
```

#### Claims usados

```text
sub    -> principal autenticado
scope  -> scopes separados por espacios o comas
scopes -> lista alternativa de scopes
exp    -> expiracion
nbf    -> no valido antes de esta fecha
iss    -> issuer opcional
aud    -> audience opcional
```

#### Scopes

El proveedor JWT reutiliza los scopes de Fase 12.1:

```text
read
write
admin
```

#### Politica de compatibilidad

`ApiKeyAuthProvider` sigue siendo el backend por defecto.

JWT solo se activa con:

```text
SECURE_VECTOR_DB_AUTH_BACKEND=jwt
```

#### Alcance

Esta fase no implementa:

```text
- login;
- refresh tokens;
- usuarios persistentes;
- OAuth2 completo;
- rotacion automatica de llaves;
- JWKS remoto.
```

#### Riesgo

Esta fase es experimental.

Para produccion real se recomienda una fase posterior con rotacion de llaves, JWKS, auditoria y politicas de expiracion mas estrictas.
