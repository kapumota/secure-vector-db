### Explain plan unificado

#### Objetivo

La Fase 6 agrega un contrato estable de explain plan para consultas ordenadas.

El objetivo es que SecureVectorDB no solo ejecute consultas, sino que tambien explique que plan de acceso eligio y por que.

#### Operaciones cubiertas

```text
get
range
```

#### Busqueda por ID

CLI:

```bash
python -m secure_vector_db.cli --db demo.sqlite explain-get 42
```

API:

```http
GET /explain/records/42
```

Ejemplo de salida:

```json
{
  "contract_version": 1,
  "operation": "get",
  "record_id": 42,
  "plan": "hybrid_ordered_index_lookup",
  "primary_index": "learned_piecewise_index",
  "fallback": "bplus_tree",
  "fallback_used": false,
  "predicted_position": 40,
  "search_window": [0, 84],
  "model_status": "healthy",
  "found": true
}
```

#### Busqueda por rango

CLI:

```bash
python -m secure_vector_db.cli --db demo.sqlite explain-range 10 20
```

API:

```http
GET /explain/range?start=10&end=20
```

Ejemplo de salida:

```json
{
  "contract_version": 1,
  "operation": "range",
  "range": [10, 20],
  "plan": "bplus_tree_range_scan",
  "primary_index": "bplus_tree",
  "fallback": null,
  "fallback_used": false,
  "result_count": 11,
  "order": "ascending_record_id"
}
```

#### Politica de indices

Para busquedas exactas por ID, el sistema puede usar el indice aprendido como acelerador cuando esta saludable. Si no resuelve la busqueda, el B+ Tree conserva la respuesta exacta.

Para busquedas por rango, el B+ Tree se mantiene como indice ordenado exacto.

#### Compatibilidad

El comando `explain-id` se mantiene como alias compatible, pero la salida recomendada para nuevas integraciones es `explain-get`.

#### Alcance

Esta fase no cambia la semantica de busqueda. Solo agrega un contrato estable de explicabilidad para operaciones ordenadas.
