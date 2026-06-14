### Auth middleware y scopes basicos

#### Objetivo

La Fase 12.1 agrega una capa de scopes basicos sobre `AuthProvider`.

El objetivo es preparar autorizacion minima por operacion sin romper `X-API-Key` ni reemplazar el servidor actual.

#### Scopes definidos

```text
read
write
admin
```

#### Significado de scopes

```text
read  -> busqueda, health, explain y consultas
write -> insert, delete y futuras operaciones PATCH
admin -> retrain, configuracion y operaciones administrativas
```

`admin` permite tambien operaciones `read` y `write`.

#### Componentes agregados

```text
AuthenticatedPrincipal
require_auth_scope()
require_read_scope
require_write_scope
require_admin_scope
authenticate_with_scope()
scope_for_endpoint()
ENDPOINT_SCOPE_MAP
```

#### Compatibilidad

`require_api_key()` sigue existiendo.

La fase no elimina el mecanismo actual `X-API-Key`. La nueva capa permite migrar endpoints de forma gradual hacia dependencias con scopes.

#### Variables de entorno

```text
SECURE_VECTOR_DB_AUTH_SCOPES=read,write,admin
SECURE_VECTOR_DB_AUTH_BACKEND=api_key
SECURE_VECTOR_DB_API_KEY=clave-local
```

#### Uso esperado

```python
from secure_vector_db.api.auth_scopes import require_read_scope

@app.get("/records/{record_id}")
def get_record(record_id: int, principal = Depends(require_read_scope)):
    ...
```

#### Politica de errores

```text
401 -> autenticacion faltante o invalida
403 -> autenticacion valida pero scope insuficiente
```

#### Alcance

Esta fase no implementa JWT ni OAuth2.

La integracion completa por endpoint puede hacerse de forma incremental para evitar romper compatibilidad.
