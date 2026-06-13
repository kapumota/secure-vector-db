### Indices aprendidos

#### Objetivo

La Fase 1 agrega un indice aprendido lineal por segmentos para claves enteras ordenadas.

El componente es experimental y no reemplaza al B+ Tree. En esta fase se mantiene aislado para validar su comportamiento antes de conectarlo al flujo de busqueda por `record_id`.

#### Diseno

`LearnedPiecewiseIndex` aproxima la posicion de una clave dentro de una lista ordenada.

El flujo interno es:

```text
clave
prediccion lineal por segmento
posicion aproximada
ventana local de busqueda
```

Cada segmento guarda:

```text
clave inicial
clave final
posicion inicial
posicion final
pendiente
intercepto
error maximo local
error promedio local
```

#### Garantias de esta fase

El indice aprendido cumple estas reglas:

```text
- Solo acepta claves enteras estrictamente ordenadas.
- No acepta claves duplicadas.
- No predice posiciones fuera del rango entrenado.
- Mantiene el error observado dentro del umbral cuando el entrenamiento lo permite.
- Devuelve una ventana inclusiva alrededor de la prediccion.
- No intercepta todavia las busquedas reales de SecureVectorDB.
```

#### Alcance

Esta fase no modifica `SecureVectorDB.search_by_id`.

El B+ Tree sigue siendo el indice exacto del sistema. La integracion hibrida con fallback corresponde a una fase posterior.

#### Validacion

```bash
ruff check .
mypy secure_vector_db
python -m pytest -q
```

#### Siguiente fase

La Fase 2 debe agregar un enrutador de indice ordenado que use el indice aprendido como acelerador y el B+ Tree como fallback exacto.

#### Fase 2 - Indice hibrido con fallback

La Fase 2 conecta el indice aprendido con una garantia exacta mediante B+ Tree.

El flujo de busqueda por ID queda asi:

```text
search_by_id(record_id)
prediccion con LearnedPiecewiseIndex
busqueda local en ventana inclusiva
si encuentra el ID, retorna
si no encuentra, fallback a B+ Tree
```

El B+ Tree sigue siendo la fuente exacta de verdad. El indice aprendido solo acelera cuando su ventana local contiene la clave buscada.

#### Metricas del indice ordenado

Las metricas expuestas son:

```text
learned_enabled
learned_segments
learned_max_error
learned_avg_error
learned_fallback_count
learned_fallback_rate
learned_window_size
learned_lookup_count
learned_trained_keys
learned_disabled_reason
```

#### Seguridad del fallback

Cuando se inserta o elimina un registro, el indice aprendido se desactiva. Esto evita consultar un modelo entrenado sobre una version anterior del conjunto de claves.

Para reactivar el camino aprendido se debe entrenar nuevamente:

```python
db.train_learned_index(max_error=64)
```

#### API

```http
GET /indexes/ordered/stats
```

#### CLI

```bash
python -m secure_vector_db.cli --db demo.sqlite train-learned-index --max-error 64
python -m secure_vector_db.cli --db demo.sqlite index-stats
```

El entrenamiento del indice aprendido en esta fase es en memoria. La persistencia del modelo aprendido queda reservada para una fase posterior.

#### Observabilidad y benchmark

La Fase 3.5 agrega explain plan, endpoint de explicabilidad, CLI de explicabilidad, benchmark comparativo y policy recommendation.

Documento relacionado:

docs/LEARNED_OBSERVABILITY.md

#### Persistencia del modelo aprendido

La Fase 4 agrega persistencia SQLite para segmentos y metadata del indice aprendido.

Documento relacionado:

```text
docs/LEARNED_INDEX_PERSISTENCE.md
```
