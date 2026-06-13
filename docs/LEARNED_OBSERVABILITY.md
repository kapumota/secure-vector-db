### Observabilidad de indices aprendidos

#### Objetivo

Esta fase agrega explain plan, benchmark comparativo y policy recommendation para el indice ordenado hibrido.

El objetivo es medir si el indice aprendido conviene antes de persistirlo. El sistema debe poder explicar cuando usa el modelo, cuando cae a B+ Tree y que costo real tiene cada camino.

#### Explain plan

La base expone:

```python
db.explain_search_by_id(record_id)
```

La respuesta incluye:

```text
record_id
strategy
learned_enabled
predicted_position
window_start
window_end
window_size
found_in_window
fallback_used
segments
max_error
avg_error
found
bplus_found
latency_ns
```

#### API

```http
GET /indexes/ordered/explain/{record_id}
```

#### CLI

```bash
python -m secure_vector_db.cli --db demo.sqlite explain-id 42
```

#### Benchmark comparativo

```bash
python benchmarks/benchmark_ordered_index.py \
  --records 10000 \
  --queries 2000 \
  --distribution uniform \
  --max-error 64 \
  --json reports/ordered-index-benchmark.json
```

Distribuciones soportadas:

```text
uniform
gapped
skewed
clustered
missing-heavy
```

#### Metricas del benchmark

```text
bplus_latency_avg_ns
learned_latency_avg_ns
bplus_latency_p95_ns
learned_latency_p95_ns
fallback_rate
window_size
segments
max_error
avg_error
trained_keys
query_count
hit_count
miss_count
```

#### Policy recommendation

El benchmark genera una recomendacion simple:

```text
enable
disable
```

La recomendacion usa tres reglas:

```text
fallback_rate <= threshold
learned p95 <= bplus p95 * factor
observed_max_error <= configured_max_error
```

Esta fase no persiste el modelo aprendido. La persistencia queda reservada para la siguiente fase.
