### Baseline de seguridad de release

#### Objetivo

La Fase 9 define una baseline minima de seguridad para preparar un release serio de SecureVectorDB.

Esta fase no convierte el proyecto en una plataforma enterprise. Su objetivo es cerrar riesgos basicos, documentar limites reales y dejar una ruta clara hacia mecanismos mas robustos.

#### Controles incluidos

```text
- Dockerfile con usuario no root.
- Auditoria local de baseline con scripts/security_audit.py.
- Workflow de seguridad basica en GitHub Actions.
- Documentacion de limites de SQLite, X-API-Key y rate limiting en memoria.
- Politica explicita para secretos y despliegue.
- Pruebas que verifican contrato de seguridad de release.
```

#### Autenticacion actual

La API usa `X-API-Key` como mecanismo simple de autenticacion.

Esto es suficiente para:

```text
- demo local;
- pruebas controladas;
- despliegues internos pequenos;
- release experimental estable.
```

No reemplaza:

```text
- OAuth2;
- JWT con rotacion;
- scopes por usuario;
- integracion con proveedor externo;
- gestion avanzada de sesiones.
```

#### Rate limiting actual

El rate limiting actual es en memoria.

Esto funciona para un proceso unico, pero no es suficiente para multiples workers o multiples instancias.

Ruta recomendada posterior:

```text
RateLimiterBackend
MemoryRateLimiter
RedisRateLimiter
```

#### Backend persistente actual

SQLite sigue siendo el backend persistente principal.

Esto es honesto y apropiado para el release actual, pero la escalabilidad futura requiere una capa de abstraccion de almacenamiento.

Ruta recomendada posterior:

```text
RecordStoreProtocol
SQLiteRecordStore
PostgresRecordStore experimental
PgVectorStore experimental
```

#### Integridad Merkle

El Merkle root actual prioriza claridad y verificabilidad.

Para datasets grandes, la optimizacion futura debe ser un Merkle incremental que actualice solo las ramas afectadas por insert, delete o update.

#### PATCH parcial

El proyecto todavia no promete actualizacion parcial de metadata.

La fase posterior recomendada es `PATCH /records/{record_id}/metadata`, sin regenerar embedding cuando el texto no cambia.

#### Politica de secretos

```text
- No versionar claves reales.
- No versionar archivos .env locales.
- No versionar bases SQLite de prueba.
- No versionar reportes con datos sensibles.
- Usar variables de entorno para claves de despliegue.
```

#### Estado de seguridad

```text
baseline_release
```

El estado `baseline_release` significa que existe una base razonable para release experimental, no una garantia de seguridad enterprise.
#### Storage abstraction layer

La Fase 10 agrega `storage abstraction layer` para separar el contrato de almacenamiento de la implementacion SQLite actual.

Esto prepara una ruta posterior hacia:

```text
PostgresRecordStore experimental
PgVectorStore experimental
RedisRateLimiter
```

SQLite sigue siendo el backend persistente principal en el release actual.


#### Redis rate limiting distribuido

El backend `RedisRateLimiter` habilita rate limiting distribuido para despliegues con multiples workers o replicas.
#### Auth provider layer

La Fase 12.0 agrega `Auth provider layer` para separar la autenticacion actual de la logica HTTP.

El backend estable sigue siendo `ApiKeyAuthProvider` sobre `X-API-Key`.

Backends posteriores quedan planificados:

```text
AuthMiddleware con scopes basicos
JwtAuthProvider experimental
OAuth2 fuera del alcance inmediato
```

#### Auth middleware compatible

La capa de Auth middleware permite aplicar scopes basicos de forma gradual sin romper `X-API-Key`.
