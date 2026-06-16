<!-- badges-release-start -->
[![CI](https://github.com/kapumota/secure-vector-db/actions/workflows/ci.yml/badge.svg)](https://github.com/kapumota/secure-vector-db/actions/workflows/ci.yml)
[![Security baseline](https://github.com/kapumota/secure-vector-db/actions/workflows/security-baseline.yml/badge.svg)](https://github.com/kapumota/secure-vector-db/actions/workflows/security-baseline.yml)
[![Lanzamiento](https://img.shields.io/badge/lanzamiento-v1.0.0-success)](https://github.com/kapumota/secure-vector-db/releases/tag/v1.0.0)
[![Version](https://img.shields.io/badge/version-1.0.0-informational)](https://github.com/kapumota/secure-vector-db/blob/main/VERSION)
[![Tag](https://img.shields.io/badge/tag-v1.0.0-informational)](https://github.com/kapumota/secure-vector-db/releases/tag/v1.0.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-informational)](https://github.com/kapumota/secure-vector-db/blob/main/pyproject.toml)
[![Licencia](https://img.shields.io/badge/licencia-MIT-informational)](https://github.com/kapumota/secure-vector-db/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-80%2B-success)](https://github.com/kapumota/secure-vector-db/blob/main/docs/COVERAGE_AND_DOCKER_SMOKE.md)
[![Supply chain](https://img.shields.io/badge/supply_chain-0_vulnerabilidades-success)](https://github.com/kapumota/secure-vector-db/blob/main/docs/SUPPLY_CHAIN_SECURITY.md)
[![Docker smoke](https://img.shields.io/badge/docker_smoke-passing-success)](https://github.com/kapumota/secure-vector-db/blob/main/docs/COVERAGE_AND_DOCKER_SMOKE.md)
[![API](https://img.shields.io/badge/api-estable-success)](https://github.com/kapumota/secure-vector-db/blob/main/docs/API_CONTRACT.md)
[![CLI](https://img.shields.io/badge/cli-contrato_estable-success)](https://github.com/kapumota/secure-vector-db/blob/main/docs/CLI_CONTRACT.md)
[![Storage](https://img.shields.io/badge/storage-SQLite-informational)](https://github.com/kapumota/secure-vector-db/blob/main/docs/STORAGE.md)
[![Merkle](https://img.shields.io/badge/merkle-evidencia_verificable-informational)](https://github.com/kapumota/secure-vector-db/blob/main/docs/MERKLE_EVIDENCE.md)
[![Docker](https://img.shields.io/badge/docker-compose-informational)](https://github.com/kapumota/secure-vector-db/blob/main/docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-informational)](https://github.com/kapumota/secure-vector-db/blob/main/API.md)
[![SQLite](https://img.shields.io/badge/backend-SQLite-informational)](https://github.com/kapumota/secure-vector-db/blob/main/docs/STORAGE.md)
[![Release gated](https://img.shields.io/badge/release-gated-success)](https://github.com/kapumota/secure-vector-db/actions/workflows/ci.yml)
[![release-candidate-check](https://img.shields.io/badge/release_candidate_check-passing-success)](https://github.com/kapumota/secure-vector-db/blob/main/docs/RELEASE_CANDIDATE.md)
[![final-release-check](https://img.shields.io/badge/final_release_check-passing-success)](https://github.com/kapumota/secure-vector-db/blob/main/docs/RELEASE.md)
<!-- badges-release-end -->

### SecureVectorDB

SecureVectorDB es un motor local de recuperación vectorial verificable escrito en Python. Permite guardar textos con metadatos, generar embeddings, consultar por ID, consultar por rango, ejecutar búsqueda vectorial y verificar la integridad del dataset mediante una raíz Merkle.

El proyecto está pensado como una base técnica reproducible para estudiar almacenamiento, búsqueda semántica, índices, API REST, persistencia local y verificación de integridad.

SecureVectorDB se presenta como un producto versionado estable inicial: un motor local de recuperación vectorial verificable con contrato público, evidencia de release y límites de alcance explícitos. No es una base de datos distribuida, no implementa replicación, consenso, sharding, alta disponibilidad ni control multiusuario enterprise.

#### Alcance actual

| Área | Estado |
|---|---|
| Persistencia | SQLite local |
| API | FastAPI con endpoints básicos |
| CLI | Inserción, consulta, rango, búsqueda, verificación y demo |
| Índice ordenado | B+ Tree para consultas por ID y rango |
| Índice vectorial base | KD-Tree sin dependencias nativas adicionales |
| Índices vectoriales opcionales | FAISS y HNSW mediante dependencias separadas |
| Embeddings base | Hash determinístico para pruebas y CI |
| Embeddings semánticos | `sentence-transformers` opcional |
| Integridad | Merkle root y evidencia verificable |
| Seguridad base | `X-API-Key`, rate limiting local y contenedor no root |
| Release | Pruebas, coverage gate, smoke test Docker y evidencia de release |

#### Decisiones de diseño

SecureVectorDB prioriza un flujo local y reproducible antes que una arquitectura distribuida.

- SQLite es el backend persistente estable. Es suficiente para demos, pruebas, uso local y prototipos, pero no reemplaza un motor cliente-servidor para alta concurrencia.
- `hash` es el generador de embeddings por defecto para mantener pruebas rápidas y determinísticas. Para una demo semántica real debe usarse `sentence-transformers`.
- `kd_tree` es el índice vectorial base. FAISS y HNSW son opcionales porque requieren librerías nativas.
- La raíz Merkle sirve para detectar cambios inesperados cuando se compara contra una raíz o evidencia esperada. No reemplaza autenticación, backups, auditoría externa ni controles de acceso.
- Redis, JWT, scopes, Merkle incremental e índices aprendidos se tratan como extensiones experimentales o especializadas, no como el camino principal de uso.

#### Instalación

```bash
python -m venv .secure_db
source .secure_db/bin/activate
pip install -r requirements.txt
```

En Windows PowerShell:

```powershell
python -m venv .secure_db
.\.secure_db\Scripts\Activate.ps1
pip install -r requirements.txt
```

Para desarrollo:

```bash
pip install -r requirements-dev.txt
```

Dependencias opcionales:

```bash
pip install -r requirements-ann.txt
pip install -r requirements-embeddings.txt
```

#### Uso rápido con CLI

Demo en memoria:

```bash
python -m secure_vector_db.cli --index kd_tree --embedding hash demo
```

Demo persistente con SQLite:

```bash
python -m secure_vector_db.cli --db demo.sqlite insert 1 "base de datos vectorial" --topic database
python -m secure_vector_db.cli --db demo.sqlite insert 2 "integridad con merkle" --topic crypto
python -m secure_vector_db.cli --db demo.sqlite insert 3 "busqueda semantica" --topic ai

python -m secure_vector_db.cli --db demo.sqlite get 1
python -m secure_vector_db.cli --db demo.sqlite range 1 3
python -m secure_vector_db.cli --db demo.sqlite search "integridad" -k 2
python -m secure_vector_db.cli --db demo.sqlite verify
```

#### API REST

Configurar variables mínimas:

```bash
export SECURE_VECTOR_DB_PATH=api.sqlite
export SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
export SECURE_VECTOR_DB_VECTOR_INDEX=kd_tree
export SECURE_VECTOR_DB_EMBEDDING_MODEL=hash
```

Levantar el servidor:

```bash
uvicorn secure_vector_db.api.server:app --reload
```

Endpoints principales:

| Método | Ruta | Uso |
|---|---|---|
| `GET` | `/health` | Estado del servicio |
| `POST` | `/records` | Inserta o reemplaza un registro |
| `GET` | `/records/{record_id}` | Consulta por ID |
| `DELETE` | `/records/{record_id}` | Elimina un registro |
| `GET` | `/range?start=1&end=5` | Consulta por rango |
| `GET` | `/search?q=texto&k=3` | Búsqueda vectorial |
| `GET` | `/verify` | Verificación de integridad |
| `POST` | `/verify/assert` | Verificación estricta |

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/records \
  -H "Content-Type: application/json" \
  -H "X-API-Key: una-clave-larga-y-secreta" \
  -d '{"record_id":1,"text":"integridad con merkle","metadata":{"topic":"crypto"}}'

curl "http://127.0.0.1:8000/search?q=integridad&k=3" \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

La documentación interactiva queda disponible en:

```text
http://127.0.0.1:8000/docs
```

#### Docker

```bash
cp .env.example .env
docker compose up --build
```

El servicio usa un volumen persistente para conservar la base SQLite entre reinicios del contenedor.

#### Índices y embeddings

| Configuración | Recomendación |
|---|---|
| `--index kd_tree --embedding hash` | Pruebas, CI y demo liviana |
| `--index faiss --embedding sentence_transformers` | Demo semántica con dependencia nativa |
| `--index hnsw --embedding sentence_transformers` | Búsqueda aproximada experimental |
| `--index auto` | Conveniente para demo, menos explícito para producción |

Ejemplo con embeddings reales:

```bash
python -m secure_vector_db.cli \
  --index faiss \
  --embedding sentence_transformers \
  --embedding-model-name sentence-transformers/all-MiniLM-L6-v2 \
  demo
```

#### Pruebas y verificación

```bash
pytest -q
make coverage-check
make docker-smoke-test
make release-check
```

Benchmark básico:

```bash
mkdir -p reports
python benchmarks/benchmark.py \
  --records 1000 \
  --queries 100 \
  --index kd_tree \
  --json reports/kd_tree.json \
  --csv reports/kd_tree.csv
```

#### Documentación

El README solo cubre el camino principal. La documentación detallada se mantiene separada para evitar duplicación.

| Documento | Contenido |
|---|---|
| `docs/INDEX.md` | Índice maestro de documentación técnica |
| `API.md` | Uso detallado de la API |
| `SECURITY.md` | Política de seguridad del repositorio |
| `docs/API_CONTRACT.md` | Contrato público de endpoints |
| `docs/CLI_CONTRACT.md` | Contrato público de CLI |
| `docs/ERRORS.md` | Política de errores |
| `docs/STORAGE.md` | Alcance del almacenamiento SQLite y abstracción interna |
| `docs/RATE_LIMITING.md` | Rate limiting local y Redis opcional |
| `docs/AUTH.md` | Autenticación por API key y proveedor interno |
| `docs/MERKLE_EVIDENCE.md` | Evidencia verificable de integridad |
| `docs/RELEASE_EVIDENCE.md` | Evidence pack y endurecimiento de release. |
| `docs/MERKLE_INCREMENTAL.md` | Merkle incremental como extensión especializada. |
| `docs/DEPLOYMENT_SECURITY.md` | Límites y recomendaciones de despliegue |
| `docs/SUPPLY_CHAIN_SECURITY.md` | SBOM y revisión de dependencias |
| `docs/VERSIONING.md` | Versionado y contrato de release |

Los documentos sobre JWT, scopes, Merkle incremental, índices aprendidos y Redis describen extensiones especializadas. No son necesarios para ejecutar el flujo base.

#### Limitaciones

- SQLite es local y no está orientado a alta concurrencia multiusuario.
- No hay replicación distribuida, consenso ni sharding.
- El modo `hash` no representa similitud semántica real.
- FAISS, HNSW y `sentence-transformers` aumentan el peso de instalación.
- La verificación Merkle detecta cambios al comparar contra evidencia esperada, pero no impide modificaciones por sí sola.
- JWT, scopes, Redis e índices aprendidos deben considerarse extensiones experimentales hasta tener integración y operación sostenida.

#### Licencia

MIT.
