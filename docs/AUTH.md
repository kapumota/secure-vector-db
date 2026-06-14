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
