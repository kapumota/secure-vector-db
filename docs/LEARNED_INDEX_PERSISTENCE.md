### Persistencia del indice aprendido

#### Objetivo

La Fase 4 permite que el modelo aprendido no se pierda al cerrar y reabrir una base SQLite.

El sistema persiste los segmentos del modelo y metadata compacta. Al reabrir la base, calcula una huella de las claves actuales y carga el modelo solo si la huella coincide con la metadata guardada.

#### Tablas y metadata

Los segmentos se guardan en SQLite:

```sql
CREATE TABLE learned_index_segments (
    index_name TEXT NOT NULL,
    segment_id INTEGER NOT NULL,
    start_key INTEGER NOT NULL,
    end_key INTEGER NOT NULL,
    start_position INTEGER NOT NULL,
    end_position INTEGER NOT NULL,
    slope REAL NOT NULL,
    intercept REAL NOT NULL,
    max_error INTEGER NOT NULL,
    avg_error REAL NOT NULL,
    PRIMARY KEY(index_name, segment_id)
);
```

La metadata se guarda en `kv_meta` con la clave:

```text
learned_index:record_id:metadata
```

La metadata incluye:

```text
format_version
trained_keys
max_error_configured
max_error_observed
avg_error_observed
window_size
segments
key_fingerprint
created_at
```

#### Validez del modelo

El modelo aprendido solo se carga si:

```text
- existe metadata,
- existen segmentos,
- la cantidad de segmentos coincide,
- el fingerprint de claves actuales coincide con el fingerprint persistido.
```

Si los datos cambian por insercion o eliminacion, el modelo aprendido se desactiva y se elimina su estado persistido.

#### Alcance

Esta fase no implementa drift detection avanzado. La deteccion de drift y reentrenamiento automatico quedan para una fase posterior.
