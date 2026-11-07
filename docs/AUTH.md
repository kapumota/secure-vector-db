### Auth provider layer

#### Objetivo

La Fase 12.0 agrega una capa base de proveedores de autenticacion.

El objetivo es separar el mecanismo actual `X-API-Key` de la logica HTTP y preparar proveedores futuros sin romper el contrato publico de API.

#### Estado actual

```text
Backend estable: ApiKeyAuthProvider
Backend de pruebas: DisabledAuthProvider
Backend JWT: planificado
OAuth2 completo: fuera de esta fase
```

#### Contratos agregados

```text
AuthProvider
AuthDecision
ApiKeyAuthProvider
DisabledAuthProvider
build_auth_provider_from_env()
auth_provider_info()
```

#### Variables de entorno

```text
SECURE_VECTOR_DB_AUTH_BACKEND=api_key
SECURE_VECTOR_DB_AUTH_BACKEND=disabled
SECURE_VECTOR_DB_API_KEY=clave-local
SECURE_VECTOR_DB_API_KEYS=clave-a,clave-b
```

#### ApiKeyAuthProvider

`ApiKeyAuthProvider` mantiene compatibilidad con el header actual:

```text
X-API-Key
```

La fase permite una clave o varias claves separadas por comas para preparar rotacion simple.

#### DisabledAuthProvider

`DisabledAuthProvider` existe solo para pruebas controladas.

No debe usarse en despliegues reales.

#### Politica de compatibilidad

La Fase 12.0 no cambia el contrato publico de la API.

`X-API-Key` sigue siendo el mecanismo estable del release actual.

#### Alcance

Esta fase no implementa:

```text
- JWT;
- OAuth2;
- RBAC;
- scopes por endpoint;
- refresh tokens;
- usuarios persistentes.
```

#### Ruta posterior

```text
Fase 12.1 - Auth middleware y scopes basicos
Fase 12.2 - JWT experimental
```
#### Fase 12.1 - Auth middleware y scopes basicos

La fase 12.1 agrega scopes `read`, `write` y `admin` sobre `AuthProvider`.

La documentacion completa esta en:

```text
docs/AUTH_SCOPES.md
```
#### Fase 12.2 - JWT experimental

La fase 12.2 agrega `JwtAuthProvider` como backend experimental.

La documentacion completa esta en:

```text
docs/AUTH_JWT_EXPERIMENTAL.md
```

#### Endurecimiento de autenticacion

La API no acepta implicitamente la clave publica de desarrollo.

Cuando SECURE_VECTOR_DB_API_KEY o SECURE_VECTOR_DB_API_KEYS
estan configuradas, solo esas claves se consideran validas.

La variable SECURE_VECTOR_DB_ALLOW_DEV_API_KEY=true habilita
la clave predeterminada exclusivamente cuando no hay otras
claves configuradas. Solo debe utilizarse en pruebas locales.

Sin claves configuradas y sin habilitacion explicita de
desarrollo, los endpoints protegidos rechazan la solicitud.

La autenticacion por API key no sustituye TLS ni una revision
de seguridad para un despliegue publico.
