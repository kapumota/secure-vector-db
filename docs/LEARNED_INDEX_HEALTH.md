### Salud del indice aprendido

#### Objetivo

La Fase 5 agrega diagnostico de salud para el indice aprendido.

El objetivo es evitar que el learned index sea tratado como una fuente magica de verdad. El indice aprendido se mantiene como acelerador controlado y el B+ Tree sigue siendo la fuente exacta para busquedas por ID.

#### Estados

El diagnostico puede devolver:

```text
healthy
degraded
needs_retrain
disabled
```

#### Campos principales

```text
status
recommendation
reason
learned_enabled
learned_persisted
persisted_model_valid
fallback_rate
fallback_threshold
max_observed_error
avg_observed_error
configured_max_error
trained_key_count
current_key_count
inserts_since_training
distribution_changed
needs_retrain
```

#### API

```http
GET /indexes/learned/health
```

#### CLI

```bash
python -m secure_vector_db.cli --db demo.sqlite index-health
python -m secure_vector_db.cli --db demo.sqlite retrain-learned-index --max-error 64
```

#### Criterio de seguridad

```text
- Ninguna busqueda exacta depende exclusivamente del modelo aprendido.
- Si el modelo se degrada, el sistema sigue respondiendo con B+ Tree.
- Si los datos cambian, el modelo puede marcarse como needs_retrain.
- El reentrenamiento es explicito y no ocurre de forma silenciosa.
```

#### Alcance

Esta fase no implementa reentrenamiento automatico. La politica es conservadora: diagnosticar, recomendar y permitir reentrenamiento explicito.
