### Storage abstraction layer

#### Objetivo

La Fase 10 agrega una capa de contratos de almacenamiento para preparar SecureVectorDB para backends futuros sin reemplazar SQLite todavia.

El objetivo no es introducir PostgreSQL en esta fase. El objetivo es separar contrato, implementacion actual y ruta de extension.

#### Estado actual

```text
Backend persistente estable: SQLite
Backend vectorial externo: no incluido
Backend PostgreSQL pgvector: planificado
```

SQLite sigue siendo la fuente durable principal del release actual.

#### Contratos agregados

```text
PersistentRecordStore
VolatileRecordStore
StorageBackendInfo
create_persistent_record_store()
```

#### PersistentRecordStore

Contrato minimo esperado:

```text
upsert(record)
delete(record_id)
get(record_id)
all()
count()
set_meta(key, value)
get_meta(key, default)
close()
```

#### VolatileRecordStore

Contrato minimo esperado:

```text
insert(record)
delete(record_id)
get(record_id)
all()
__len__()
```

#### Factory persistente

Uso esperado:

```python
from secure_vector_db.storage.factory import create_persistent_record_store

store = create_persistent_record_store("sqlite", "demo.sqlite")
```

#### Politica de compatibilidad

La Fase 10 no cambia la semantica de `SecureVectorDB.open()`.

El backend SQLite sigue funcionando como antes. La nueva capa permite escribir pruebas de contrato y preparar backends futuros.

#### Backends futuros

Ruta recomendada:

```text
PostgresRecordStore experimental
PgVectorStore experimental
StorageBackendConfig
migraciones versionadas
tests opcionales con docker compose
```

#### Limites

Esta fase no implementa PostgreSQL, pgvector, sharding ni replicacion.

Tambien evita mover toda la base a una arquitectura nueva para reducir riesgo antes del release.
