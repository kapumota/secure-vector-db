### SecureVectorDB 

**SecureVectorDB** es una base de datos vectorial verificable desarrollada en Python. Integra almacenamiento persistente, búsqueda semántica, estructuras de índices, autenticación por API key, verificación de integridad mediante Merkle Tree, API REST con FastAPI, Docker, pruebas automatizadas y benchmarks reproducibles.

El objetivo del proyecto es demostrar cómo almacenar documentos o textos, consultarlos de forma eficiente y verificar que los datos no hayan sido alterados.

#### Problema que resuelve

Cuando se almacenan muchos documentos, no basta con guardarlos en una base de datos tradicional. También es necesario:

- buscar información de forma rápida,
- recuperar documentos por identificador,
- realizar consultas por rango,
- encontrar textos similares por significado aproximado,
- verificar que los datos almacenados no fueron modificados,
- exponer el sistema mediante una API segura.

SecureVectorDB aborda estos problemas combinando técnicas de bases de datos, criptografía e inteligencia artificial.

#### Solución propuesta

SecureVectorDB permite:

- almacenar registros con texto, metadatos y embeddings,
- consultar documentos por ID,
- consultar documentos por rango usando un B+ Tree,
- realizar búsqueda vectorial usando KD-Tree, FAISS o HNSW,
- verificar integridad mediante Merkle root SHA-256,
- persistir datos localmente con SQLite,
- acceder al sistema mediante CLI o API REST,
- proteger endpoints mediante `X-API-Key`,
- medir rendimiento con benchmarks.


#### Características principales

- **Persistencia SQLite:** los datos sobreviven reinicios del servidor o de la CLI.
- **B+ Tree:** índice ordenado para búsquedas por ID y rangos.
- **Índice vectorial configurable:** soporte para `kd_tree`, `faiss`, `hnsw` y `auto`.
- **Merkle Tree:** verificación de integridad del dataset.
- **FastAPI:** API REST con Swagger/OpenAPI.
- **API Key:** autenticación para operaciones protegidas.
- **Rate limiting:** control básico de abuso por cliente/API key.
- **Docker:** ejecución containerizada con volumen persistente.
- **CLI:** comandos para insertar, borrar, buscar, consultar rangos, verificar y ejecutar demostraciones.
- **Benchmarks:** medición de inserción, búsqueda, verificación, memoria y tamaño SQLite.
- **CI:** configuración para pruebas automáticas con GitHub Actions.
- **Embeddings configurables:** modo liviano hash-based y modo semántico real con `sentence-transformers`.


#### Estado del proyecto

El proyecto está preparado como **software base inicial** de un sistema de recuperación semántica verificable.

No se presenta como una base de datos distribuida enterprise completamente terminada. Para ese nivel todavía serían necesarios componentes como replicación distribuida, consenso, monitoreo avanzado, control multiusuario robusto y escalabilidad horizontal.


#### Arquitectura del proyecto

```text
SecureVectorDB/
  secure_vector_db/
    api/
      server.py                  # API FastAPI, OpenAPI, auth y rate limiting
    cli.py                       # Interfaz de línea de comandos
    database.py                  # Núcleo de la base, índices, locks y Merkle
    errors.py                    # Errores controlados del dominio
    storage/
      sqlite_store.py            # Persistencia durable SQLite
      record_store.py            # Store en memoria
    indexes/
      bplus_tree.py              # B+ Tree para ID y rangos
      kd_tree_vector_index.py    # Índice vectorial KD-Tree
      faiss_vector_index.py      # Índice opcional FAISS
      hnsw_vector_index.py       # Índice opcional HNSW
      factory.py                 # Selección de backend vectorial
    ml/
      embeddings.py              # Generación de embeddings
  tests/                         # Pruebas unitarias e integración
  benchmarks/                    # Benchmark reproducible
  deploy/                        # Configuración de despliegue
  API.md                         # Documentación detallada de la API
  Dockerfile                     # Imagen de ejecución
  docker-compose.yml             # Servicio con volumen persistente
  pyproject.toml                 # Configuración del proyecto Python
  requirements.txt               # Dependencias base
  requirements-dev.txt           # Dependencias para pruebas/desarrollo
  requirements-ann.txt           # Dependencias opcionales FAISS/HNSW
  requirements-embeddings.txt    # Dependencias opcionales para embeddings reales
  .env.example                   # Variables de entorno de ejemplo
```

**Requisito:** Python 3.10 o superior.

#### Instalación

Crea y activa un entorno virtual:

```bash
python -m venv .secure_db
```

En Linux o macOS:

```bash
source .secure_db/bin/activate
```

En Windows PowerShell:

```powershell
.\.secure_db\Scripts\Activate.ps1
```

Instala la dependencias base:

```bash
pip install -r requirements.txt
```

Para desarrollo y pruebas:

```bash
pip install -r requirements-dev.txt
```

Para índices vectoriales opcionales FAISS/HNSW:

```bash
pip install -r requirements-ann.txt
```

Para embeddings semánticos reales:

```bash
pip install -r requirements-embeddings.txt
```

#### Dependencias

- `requirements.txt`: dependencias necesarias para ejecutar el sistema base.
- `requirements-dev.txt`: dependencias para pruebas y desarrollo.
- `requirements-ann.txt`: dependencias opcionales para FAISS y HNSW.
- `requirements-embeddings.txt`: dependencias opcionales para `sentence-transformers`.

#### Ejecución rápida con CLI

Ejecutamos una demostración en memoria:

```bash
python -m secure_vector_db.cli --index auto demo
```

La demostración muestra:

- inserción de registros,
- cantidad de registros almacenados,
- Merkle root,
- verificación de integridad,
- búsqueda por ID,
- búsqueda por rango,
- búsqueda semántica.


#### Persistencia con SQLite

Creamos una base persistente:

```bash
python -m secure_vector_db.cli --db demo.sqlite insert 1 "base de datos vectorial" --topic database
python -m secure_vector_db.cli --db demo.sqlite insert 2 "merkle integridad criptografica" --topic crypto
python -m secure_vector_db.cli --db demo.sqlite insert 3 "busqueda semantica con embeddings" --topic ai
```

Consultar por ID:

```bash
python -m secure_vector_db.cli --db demo.sqlite get 1
```

Consultar por rango:

```bash
python -m secure_vector_db.cli --db demo.sqlite range 1 3
```

Realizar búsqueda semántica:

```bash
python -m secure_vector_db.cli --db demo.sqlite search "integridad criptografica" -k 2
```

Verificar integridad:

```bash
python -m secure_vector_db.cli --db demo.sqlite verify
```

También se puede generar una demo persistente directamente:

```bash
python -m secure_vector_db.cli --db demo.sqlite demo --persist
```


#### API REST con FastAPI

La API permite interactuar con SecureVectorDB desde otros sistemas usando HTTP.

Configurar variables de entorno:

```bash
export SECURE_VECTOR_DB_PATH=api.sqlite
export SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
export SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=120
export SECURE_VECTOR_DB_VECTOR_INDEX=auto
```

Levantar servidor:

```bash
uvicorn secure_vector_db.api.server:app --reload
```

Abrir documentación interactiva:

```text
http://127.0.0.1:8000/docs
```

Consultar estado del servicio:

```bash
curl http://127.0.0.1:8000/health
```

Insertar un registro:

```bash
curl -X POST http://127.0.0.1:8000/records \
  -H "Content-Type: application/json" \
  -H "X-API-Key: una-clave-larga-y-secreta" \
  -d '{"record_id":1,"text":"merkle integridad criptografica","metadata":{"topic":"crypto"}}'
```

Buscar por ID:

```bash
curl http://127.0.0.1:8000/records/1 \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

Búsqueda semántica:

```bash
curl "http://127.0.0.1:8000/search?q=integridad&k=3" \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

Verificar integridad:

```bash
curl http://127.0.0.1:8000/verify \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

Probar seguridad sin API key:

```bash
curl http://127.0.0.1:8000/verify
```

La API debe rechazar la petición si falta la clave.

La documentación detallada de endpoints, autenticación, rate limiting y errores se encuentra en `API.md`.

#### Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del servicio, cantidad de registros y Merkle root |
| `POST` | `/records` | Inserta o reemplaza un documento |
| `GET` | `/records/{record_id}` | Busca un documento por ID |
| `DELETE` | `/records/{record_id}` | Elimina un documento |
| `GET` | `/range?start=1&end=5` | Consulta documentos por rango de ID |
| `GET` | `/search?q=texto&k=3` | Realiza búsqueda semántica/vectorial |
| `GET` | `/verify` | Verifica integridad del dataset |
| `POST` | `/verify/assert` | Devuelve error si la integridad no coincide |


#### Autenticación

Las rutas de datos requieren el header:

```text
X-API-Key: <tu_clave>
```

`<tu_clave>` es el mismo valor configurado en:

```bash
export SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
```

Por ejemplo:

```bash
curl http://127.0.0.1:8000/verify \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

Rutas públicas:

- `GET /health`
- `GET /docs`
- `GET /openapi.json`

Rutas protegidas:

- `POST /records`
- `GET /records/{record_id}`
- `DELETE /records/{record_id}`
- `GET /range`
- `GET /search`
- `GET /verify`
- `POST /verify/assert`

#### Docker

Crear archivo `.env` a partir del ejemplo:

```bash
cp .env.example .env
```

Editar `.env` y definir una clave segura:

```env
SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
SECURE_VECTOR_DB_PATH=/data/secure_vector_db.sqlite
SECURE_VECTOR_DB_VECTOR_INDEX=auto
SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=120
```

Levantar el servicio:

```bash
docker compose up --build
```

Si aparece un error de permisos con Docker en Linux, usar:

```bash
sudo docker compose up --build
```

O agregar el usuario al grupo `docker`:

```bash
sudo usermod -aG docker $USER
```

Después cerrar sesión y volver a entrar.

Abrir:

```text
http://127.0.0.1:8000/docs
```

El archivo `docker-compose.yml` usa un volumen persistente, por lo que la base SQLite puede sobrevivir al reinicio del contenedor.

#### Índices vectoriales

SecureVectorDB soporta varios backends de búsqueda vectorial. El backend define cómo se ejecuta la búsqueda de vecinos cercanos sobre los embeddings.

| Backend | Tipo | Dependencia | Uso recomendado |
|---|---|---|---|
| `kd_tree` | Exacto | Ninguna extra | Demo, CI, datasets pequeños/medianos |
| `faiss` | Exacto/acelerado | `faiss-cpu` | Búsqueda vectorial optimizada |
| `hnsw` | Aproximado ANN | `hnswlib` | Datasets más grandes y baja latencia |
| `auto` | Selección automática | Opcional | Intenta FAISS, luego HNSW, luego KD-Tree |

Ejemplo recomendado para demo:

```bash
python -m secure_vector_db.cli --index auto demo
```

Ejemplo usando KD-Tree directamente:

```bash
python -m secure_vector_db.cli --index kd_tree demo
```

Para usar FAISS o HNSW, primero instalar dependencias opcionales:

```bash
pip install -r requirements-ann.txt
```

Luego ejecutar:

```bash
python -m secure_vector_db.cli --index faiss demo
python -m secure_vector_db.cli --index hnsw demo
```

En la API, el índice se configura antes de levantar el servidor:

```bash
export SECURE_VECTOR_DB_VECTOR_INDEX=auto
uvicorn secure_vector_db.api.server:app --reload
```

Luego se puede verificar el servicio en:

```bash
curl http://127.0.0.1:8000/health
```

#### Embeddings

SecureVectorDB soporta embeddings configurables.

| Modo | Descripción | Uso recomendado |
|---|---|---|
| `hash` | Rápido, determinístico y liviano | Pruebas offline, CI, demos simples |
| `sentence_transformers` | Embeddings semánticos reales | Demos avanzadas y búsquedas más realistas |
| `auto` | Intenta usar `sentence_transformers` y cae a `hash` | Configuración flexible |

Ejemplo con embeddings hash-based:

```bash
python -m secure_vector_db.cli --embedding hash demo
```

Ejemplo con embeddings reales:

```bash
python -m secure_vector_db.cli \
  --embedding sentence_transformers \
  --embedding-model-name sentence-transformers/all-MiniLM-L6-v2 \
  demo
```

Ejemplo combinando FAISS y embeddings reales:

```bash
python -m secure_vector_db.cli \
  --index faiss \
  --embedding sentence_transformers \
  --embedding-model-name sentence-transformers/all-MiniLM-L6-v2 \
  demo
```

**Uso de embeddings en la API**

En modo API, los embeddings no se pasan como argumento de la CLI. Se configuran mediante variables de entorno antes de levantar el servidor FastAPI.

Ejemplo usando FAISS como índice vectorial y `sentence-transformers` como generador de embeddings:

```bash
export SECURE_VECTOR_DB_PATH=api.sqlite
export SECURE_VECTOR_DB_API_KEY=demo123
export SECURE_VECTOR_DB_VECTOR_INDEX=faiss
export SECURE_VECTOR_DB_EMBEDDING_MODEL=sentence_transformers
export SECURE_VECTOR_DB_EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

uvicorn secure_vector_db.api.server:app --reload
```

Luego la API queda disponible en:

```text
http://127.0.0.1:8000/docs
```

A partir de ese momento, cada vez que se inserta un texto mediante `POST /records`, el servidor genera internamente su embedding usando el modelo configurado.

Ejemplo de inserción:

```bash
curl -X POST http://127.0.0.1:8000/records \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo123" \
  -d '{"record_id":1,"text":"merkle integridad criptografica","metadata":{"topic":"crypto"}}'
```

Luego, cuando se consulta `/search`, la API convierte la consulta en embedding y busca los registros más similares.

Ejemplo de búsqueda semántica:

```bash
curl "http://127.0.0.1:8000/search?q=integridad%20criptografica&k=3" \
  -H "X-API-Key: demo123"
```

Si no se quieren instalar dependencias pesadas, se puede usar el modo liviano `hash`:

```bash
export SECURE_VECTOR_DB_PATH=api.sqlite
export SECURE_VECTOR_DB_API_KEY=demo123
export SECURE_VECTOR_DB_VECTOR_INDEX=auto
export SECURE_VECTOR_DB_EMBEDDING_MODEL=hash

uvicorn secure_vector_db.api.server:app --reload
```

Nota: la primera ejecución con `sentence-transformers` puede descargar el modelo y tardar más.

#### Verificación de integridad con Merkle Tree

SecureVectorDB usa un **Merkle Tree** para verificar que los datos almacenados no hayan sido modificados de forma inesperada.

Cada registro insertado en la base se convierte en una representación verificable mediante hash. De forma simplificada, el sistema toma la información del registro, como su ID, texto, metadatos y embedding, y calcula un hash criptográfico asociado a ese contenido.

Luego, los hashes de todos los registros se combinan en una estructura tipo árbol hasta obtener un único valor final llamado **Merkle root**.

```text
Registro 1 ── hash 1 ┐
                     ├── hash A ┐
Registro 2 ── hash 2 ┘          │
                                ├── Merkle root
Registro 3 ── hash 3 ┐          │
                     ├── hash B ┘
Registro 4 ── hash 4 ┘
```

El **Merkle root** representa el estado completo del dataset en un momento determinado. Si un solo registro cambia, aunque sea mínimamente, su hash también cambia. Como consecuencia, cambian los hashes superiores del árbol y finalmente cambia el Merkle root.

Esto permite detectar alteraciones en los datos.

Por ejemplo:

```text
Estado original:
registro 2 = "merkle integridad criptografica"
Merkle root = abc123...

Estado alterado:
registro 2 = "texto modificado"
Merkle root = 9f8e21...
```

Si el Merkle root calculado a partir de los datos actuales no coincide con el Merkle root esperado o almacenado, el sistema puede indicar que la integridad no es válida.

En términos prácticos, esta verificación sirve para:

- detectar modificaciones no autorizadas,
- comprobar que los datos persistidos siguen siendo consistentes,
- validar que el dataset no fue alterado manualmente,
- aumentar la confianza en los registros almacenados,
- demostrar trazabilidad e integridad criptográfica.

Comando CLI:

```bash
python -m secure_vector_db.cli --db demo.sqlite verify
```

Este comando recalcula la raíz Merkle usando los datos actuales de `demo.sqlite` y devuelve si la integridad es válida.

Comando API:

```bash
curl http://127.0.0.1:8000/verify \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

Este endpoint realiza la misma verificación desde la API. Como es una ruta protegida, requiere enviar el header `X-API-Key`.

También se puede usar:

```bash
curl -X POST http://127.0.0.1:8000/verify/assert \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

La diferencia es que `/verify` devuelve el resultado de la verificación, mientras que `/verify/assert` puede responder con error si la integridad no coincide.


#### Manejo de errores

La CLI muestra errores controlados:

```text
ERROR: start_id debe ser menor o igual que end_id
```

La API responde en formato JSON:

```json
{
  "error": "ValidationError",
  "detail": "start_id debe ser menor o igual que end_id"
}
```

#### Rate limiting y concurrencia

La API incluye un mecanismo de **rate limiting** para controlar cuántas solicitudes puede hacer un cliente en un periodo corto de tiempo.

Por defecto, SecureVectorDB permite:

```text
120 solicitudes por minuto
```

El límite se aplica por combinación de:

```text
IP del cliente + API key
```

Esto significa que dos clientes con diferentes IP o diferentes claves pueden tener contadores separados.

El **rate limiting** sirve para reducir abuso o uso excesivo de la API. Por ejemplo, evita que un cliente haga demasiadas peticiones seguidas a endpoints como:

- `POST /records`
- `GET /search`
- `GET /verify`
- `DELETE /records/{record_id}`

La configuración se realiza mediante la variable de entorno:

```bash
export SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=120
```

Si se quiere permitir más tráfico durante pruebas o benchmarks, se puede aumentar:

```bash
export SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=1000
```

Si se quiere restringir más el acceso:

```bash
export SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=30
```

Cuando un cliente supera el límite permitido, la API puede responder con un error indicando que se hicieron demasiadas solicitudes.

Ejemplo conceptual:

```json
{
  "error": "RateLimitExceeded",
  "detail": "Demasiadas solicitudes. Intente nuevamente más tarde."
}
```

También puede incluir headers de control como:

```text
Retry-After
X-RateLimit-Remaining
```

Estos headers ayudan al cliente a saber cuándo puede volver a intentar una petición y cuántas solicitudes le quedan dentro de la ventana actual.


El limitador usa una estrategia de **ventana deslizante**.

Esto significa que el sistema no cuenta simplemente por minuto fijo, sino que revisa las solicitudes realizadas durante los últimos 60 segundos.

Ejemplo con límite de `120` solicitudes por minuto:

```text
Segundo 00 ─────────────── Segundo 60
       Se cuentan las solicitudes recientes dentro de esta ventana
```

Si un cliente envía muchas solicitudes dentro de ese intervalo, el sistema empieza a rechazarlas temporalmente.

Como el limitador está implementado **en memoria**, funciona bien para una instancia local o una demo. Sin embargo, en un despliegue distribuido con varios servidores, cada instancia tendría su propio contador.

Para producción distribuida podemos usar un backend compartido como Redis.

**Concurrencia**

La concurrencia se refiere a la capacidad del sistema para manejar varias operaciones al mismo tiempo.

Por ejemplo:

```text
Cliente A inserta un registro
Cliente B ejecuta una búsqueda
Cliente C verifica integridad
```

Para evitar inconsistencias, SecureVectorDB usa bloqueos internos en operaciones críticas.

La capa principal del sistema serializa operaciones como:

- escrituras,
- borrados,
- reconstrucción de índices,
- lectura de índices,
- cálculo del Merkle root,
- verificación de integridad.

Esto evita problemas como:

- leer índices mientras están siendo reconstruidos,
- calcular un Merkle root mientras otro proceso modifica datos,
- insertar registros al mismo tiempo que se borra información relacionada,
- obtener resultados inconsistentes durante búsquedas.


#### SQLite y concurrencia

SQLite se usa como almacenamiento persistente local. Para soportar uso concurrente básico dentro del proceso de la API, el sistema lo configura de forma compatible con múltiples solicitudes manejadas por FastAPI.

En términos prácticos, esto permite que el servidor atienda varias peticiones HTTP sin corromper la base de datos.

Sin embargo, SQLite no es equivalente a una base distribuida como PostgreSQL, MySQL en clúster o sistemas NoSQL distribuidos. 

Para producción con muchos usuarios concurrentes, se recomienda evaluar una base de datos cliente-servidor o una arquitectura con cola de escritura, réplicas y almacenamiento distribuido.

#### Pruebas

Ejecutar pruebas:

```bash
pytest -q
```

Las pruebas cubren:

- inserción y consulta,
- reemplazo de registros,
- borrado,
- integridad alterada,
- dataset vacío,
- rangos inválidos,
- persistencia SQLite tras reabrir,
- documentación OpenAPI disponible,
- autenticación con API key,
- rechazo de solicitudes sin `X-API-Key`,
- comportamiento de índices,
- concurrencia básica.


#### Benchmarks

El proyecto incluye un benchmark reproducible para medir:

- cantidad de registros insertados,
- registros por segundo,
- latencia promedio,
- latencia p50, p95 y máxima,
- búsqueda por ID,
- búsqueda por rango,
- búsqueda semántica,
- tiempo de verificación Merkle,
- memoria pico,
- tamaño del archivo SQLite.

Ejecutar benchmark básico:

```bash
mkdir -p reports

python benchmarks/benchmark.py \
  --records 1000 \
  --queries 100 \
  --index kd_tree \
  --json reports/kd_tree.json \
  --csv reports/kd_tree.csv
```

Ejecutar benchmark en memoria:

```bash
python benchmarks/benchmark.py \
  --records 1000 \
  --queries 100 \
  --memory
```

Comparar backends vectoriales:

```bash
python benchmarks/benchmark.py \
  --records 5000 \
  --queries 300 \
  --compare kd_tree,faiss,hnsw \
  --json reports/ann_comparison.json \
  --csv reports/ann_comparison.csv
```

Usar embeddings reales en el benchmark:

```bash
python benchmarks/benchmark.py \
  --records 1000 \
  --queries 100 \
  --compare kd_tree,faiss,hnsw \
  --embedding sentence_transformers \
  --embedding-model-name sentence-transformers/all-MiniLM-L6-v2 \
  --json reports/semantic_embeddings_comparison.json
```

Si `faiss-cpu` o `hnswlib` no están instalados, el benchmark puede marcar esos backends como omitidos y continuar con los demás.

#### Evolución técnica por fases

SecureVectorDB fue desarrollado incrementalmente en cuatro fases principales.

#### Fase 1: índices incrementales

Se optimizó la actualización de índices para evitar reconstruir todo el B+ Tree y el índice vectorial después de cada inserción o eliminación. Ahora `insert()` y `delete()` actualizan solo el registro afectado.

#### Fase 2: índices vectoriales configurables

Se agregó una arquitectura de índices vectoriales intercambiables. El sistema usa `kd_tree` por defecto, pero puede usar `faiss`, `hnsw` o `auto` si las dependencias opcionales están instaladas.

#### Fase 3: embeddings configurables

Se incorporó soporte para distintos generadores de embeddings. El modo `hash` permite pruebas ligeras y reproducibles, mientras que `sentence_transformers` permite usar embeddings semánticos reales.

#### Fase 4: benchmarks comparativos

Se añadió un benchmark reproducible para comparar rendimiento entre `kd_tree`, `faiss` y `hnsw`, midiendo inserción, búsqueda por ID, búsqueda por rango, búsqueda semántica, verificación Merkle, memoria y tamaño SQLite.

#### CI

El proyecto incluye configuración para GitHub Actions.

El flujo automatiza:

- instalación de dependencias,
- ejecución de pruebas,
- benchmark de humo,
- validación básica del proyecto antes de integraciones o despliegues.


#### Limitaciones

- SQLite ofrece persistencia local, pero no convierte el sistema en una base distribuida completa.
- La autenticación por API key es funcional, pero para producción se recomienda JWT, OAuth2 o integración con un proveedor de identidad.
- El rate limiting está implementado en memoria, en despliegues distribuidos debería usarse Redis u otro backend compartido.
- FAISS y HNSW son opcionales y dependen de librerías nativas.
- Los embeddings hash-based son determinísticos y livianos, pero no capturan semántica profunda.
- Si se cambia el modelo de embeddings en una base persistente, puede ser necesario reinsertar o reindexar registros.
- Para producción a gran escala faltarían replicación, monitoreo, backups, métricas, trazas y coordinación multi-proceso.


#### Comandos para una demostración

Preparar entorno:

```bash
python -m venv vector
source vector/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Ejecutar demostración:

```bash
python -m secure_vector_db.cli --index auto demo
```

Probar persistencia:

```bash
python -m secure_vector_db.cli --db demo.sqlite insert 1 "base de datos vectorial segura" --topic database
python -m secure_vector_db.cli --db demo.sqlite insert 2 "merkle integridad criptografica" --topic crypto
python -m secure_vector_db.cli --db demo.sqlite search "integridad" -k 2
python -m secure_vector_db.cli --db demo.sqlite verify
```

Levantar API:

```bash
export SECURE_VECTOR_DB_PATH=api.sqlite
export SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
uvicorn secure_vector_db.api.server:app --reload
```

Ejecutar benchmark:

```bash
mkdir -p reports
python benchmarks/benchmark.py --records 1000 --queries 100 --index kd_tree --json reports/kd_tree.json --csv reports/kd_tree.csv
```


#### Licencia

```text
MIT License
```

### Limpieza local del proyecto

#### Comandos recomendados

El repositorio incluye comandos reproducibles para limpiar artefactos locales sin tocar el entorno virtual `.secure_db`.

```bash
make clean
make clean-cache
make clean-build
make clean-reports
make clean-all
```

`make clean` elimina caches y artefactos de build. `make clean-reports` se deja separado para no borrar evidencia local por accidente.

#### Explain plan

SecureVectorDB expone explain plan para inspeccionar que indice se usa en busquedas por ID y por rango.

```bash
python -m secure_vector_db.cli --db demo.sqlite explain-get 42
python -m secure_vector_db.cli --db demo.sqlite explain-range 10 20
```

#### Persistencia y recuperacion

SecureVectorDB expone diagnostico de recuperacion para validar raiz Merkle, registros persistidos e indices auxiliares reconstruibles.

```bash
python -m secure_vector_db.cli --db demo.sqlite persistence-health
```

#### Contratos publicos

La API, CLI y politica de errores tienen contratos documentados para preparar releases sin mezclar partes estables y experimentales.

```text
docs/API_CONTRACT.md
docs/CLI_CONTRACT.md
docs/ERRORS.md
```


#### Seguridad de release

SecureVectorDB incluye una baseline de seguridad para release experimental: contenedor no root, auditoria local, contrato de API con `X-API-Key` y documentacion explicita de limites.

```text
docs/SECURITY_BASELINE.md
docs/DEPLOYMENT_SECURITY.md
scripts/security_audit.py
```
#### Storage abstraction layer

SecureVectorDB mantiene SQLite como backend persistente estable, pero define contratos de almacenamiento para preparar backends futuros sin reescribir la logica principal.

```text
docs/STORAGE.md
secure_vector_db/storage/contracts.py
secure_vector_db/storage/factory.py
```
#### Redis rate limiting opcional

SecureVectorDB mantiene rate limiting en memoria por defecto y agrega backend Redis opcional para despliegues con multiples procesos o replicas.

```text
docs/RATE_LIMITING.md
requirements-redis.txt
docker-compose.redis.yml
```
#### Auth provider layer

SecureVectorDB mantiene `X-API-Key` como mecanismo estable y agrega una capa `AuthProvider` para preparar backends futuros sin romper compatibilidad.

```text
docs/AUTH.md
secure_vector_db/api/auth.py
```
#### Auth middleware y scopes basicos

SecureVectorDB agrega scopes basicos sobre `AuthProvider` para preparar autorizacion por operacion sin romper `X-API-Key`.

```text
docs/AUTH_SCOPES.md
secure_vector_db/api/auth_scopes.py
```
