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

#### Riesgos y mitigaciones

La persistencia del indice aprendido tiene riesgo medio porque modifica la carga durable de `SecureVectorDB`, agrega una tabla SQLite nueva y guarda metadata usada para activar un modelo aprendido despues de reabrir la base.

El riesgo principal no es perder datos, sino activar un modelo aprendido que ya no representa la distribucion actual de claves. Para controlar ese riesgo, el sistema mantiene el B+ Tree como fuente exacta de verdad y valida la vigencia del modelo antes de usarlo.

#### Riesgos tecnicos

```text
- Modelo aprendido obsoleto despues de inserciones o eliminaciones.
- Metadata incompleta o inconsistente en kv_meta.
- Segmentos persistidos que no coinciden con la metadata.
- Cambio de distribucion de claves entre entrenamiento y reapertura.
- Activacion accidental de un modelo entrenado sobre otra version de datos.
```

#### Controles aplicados

```text
- B+ Tree sigue siendo la fuente exacta de verdad.
- El modelo aprendido solo se carga si el fingerprint de claves coincide.
- La cantidad de segmentos persistidos debe coincidir con la metadata.
- Si el fingerprint no coincide, el modelo persistido se descarta.
- Si hay insercion o eliminacion, el learned index se desactiva.
- Si hay insercion o eliminacion, el estado persistido se elimina.
- Si el modelo no se puede cargar, la busqueda sigue funcionando por B+ Tree.
```

#### Impacto esperado

```text
Disponibilidad: baja afectacion, porque B+ Tree queda como fallback.
Integridad: riesgo controlado por fingerprint y validacion de segmentos.
Rendimiento: puede mejorar si el modelo es valido; si no, se desactiva.
Mantenibilidad: mejora porque el modelo persistido tiene metadata verificable.
```

#### Politica de recuperacion

Si la carga del modelo aprendido no es valida, el sistema debe operar en modo seguro:

```text
- desactivar learned index,
- mantener busqueda exacta por B+ Tree,
- eliminar metadata o segmentos inconsistentes,
- permitir reentrenamiento explicito.
```

#### Evidencia esperada

La fase debe estar cubierta por pruebas que validen:

```text
- persistencia de segmentos,
- reapertura de base con modelo aprendido activo,
- invalidacion despues de insercion,
- invalidacion despues de eliminacion,
- fallback correcto cuando el modelo no esta activo.
```
