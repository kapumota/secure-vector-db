### SecureVectorDB API v7

La API expone una base de datos vectorial verificable con persistencia SQLite, Merkle root, KD-Tree vectorial, rate limiting y autenticación por API key. Al iniciar, usa `SECURE_VECTOR_DB_PATH` o `secure_vector_db_api.sqlite`. La base se abre durante el ciclo de vida de FastAPI y se cierra correctamente al apagar el servicio.

#### Ejecutar localmente

```bash
export SECURE_VECTOR_DB_PATH=api.sqlite
export SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
export SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=120
uvicorn secure_vector_db.api.server:app --reload
```

Documentación interactiva:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

#### Ejecutar con Docker

```bash
cp .env.example .env
# Edita .env y cambia SECURE_VECTOR_DB_API_KEY
docker compose up --build
```

El servicio usa un volumen persistente para `/data`. Copia `.env.example` como `.env` y cambia `SECURE_VECTOR_DB_API_KEY` antes de usar información real.

#### Autenticación

Todas las rutas de datos requieren el header:

```text
X-API-Key: <tu_clave>
```

Rutas protegidas:

- `POST /records`
- `GET /records/{record_id}`
- `DELETE /records/{record_id}`
- `GET /range`
- `GET /search`
- `GET /verify`
- `POST /verify/assert`

Rutas públicas:

- `GET /health`
- `GET /docs`
- `GET /openapi.json`

Respuesta si falta o es incorrecta:

```json
{
  "detail": "API key inválida o ausente. Envíe el header X-API-Key."
}
```

#### Rate limiting

La API aplica rate limiting por IP y API key. Valor por defecto: `120` requests/minuto. Variable de entorno:

```bash
SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=120
```

Cuando se supera el límite, responde:

```json
{
  "error": "RateLimitExceeded",
  "detail": "Demasiadas solicitudes. Intente nuevamente más tarde."
}
```

También devuelve headers `Retry-After` y `X-RateLimit-Remaining`.

#### Modelo de error controlado

Errores de dominio:

```json
{
  "error": "ValidationError",
  "detail": "start_id debe ser menor o igual que end_id"
}
```

#### Endpoints

#### `GET /health`

Estado del servicio. No requiere autenticación.

```json
{
  "status": "ok",
  "records": 2,
  "root_hash": "...",
  "storage": "secure_vector_db_api.sqlite"
}
```

#### `POST /records`

Inserta o reemplaza un documento. Requiere `X-API-Key`.

```bash
curl -X POST http://127.0.0.1:8000/records \
  -H "Content-Type: application/json" \
  -H "X-API-Key: una-clave-larga-y-secreta" \
  -d '{"record_id":1,"text":"merkle integridad criptografica","metadata":{"topic":"crypto"}}'
```

Respuesta:

```json
{
  "record": {
    "record_id": 1,
    "text": "merkle integridad criptografica",
    "metadata": {"topic": "crypto"},
    "embedding": [0.0, 0.5]
  },
  "root_hash": "..."
}
```

#### `GET /records/{record_id}`

Busca por ID. Devuelve `404` si no existe.

#### `DELETE /records/{record_id}`

Elimina por ID.

```json
{"deleted": true, "root_hash": "..."}
```

#### `GET /range?start=1&end=10`

Consulta por rango usando el índice B+ Tree reconstruido en memoria desde SQLite.

#### `GET /search?q=integridad&k=3`

Búsqueda vectorial k-NN con KD-Tree exacto y embeddings hash-based.

> Nota: estos embeddings son determinísticos y ligeros. No son embeddings neuronales ni un LLM real.

#### `GET /verify`

Compara la raíz Merkle guardada contra los datos actuales.

#### `POST /verify/assert`

Devuelve `409 Conflict` si la integridad no coincide.
