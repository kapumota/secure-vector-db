### Despliegue de SecureVectorDB

Este documento describe cómo desplegar **SecureVectorDB** usando Docker, Docker Compose y plantillas opcionales para servicios cloud como Render.

El objetivo del despliegue es ejecutar la API FastAPI dentro de un contenedor, exponer el servicio por el puerto `8000` y mantener la base SQLite en un volumen persistente para que los datos no se pierdan cuando el contenedor se detenga o se reinicie.

#### Archivos relacionados con despliegue

El proyecto incluye los siguientes archivos relevantes:

```text
Dockerfile                  # Define la imagen de ejecución de la API
docker-compose.yml          # Levanta el servicio localmente con volumen persistente
.env.example                # Variables de entorno de ejemplo
deploy/README.md            # Explicación de plantillas cloud opcionales
deploy/render.example.yaml  # Plantilla opcional para Render
```

#### Variables de entorno principales

SecureVectorDB se configura mediante variables de entorno.

| Variable | Descripción | Ejemplo |
|---|---|---|
| `SECURE_VECTOR_DB_PATH` | Ruta donde se guarda la base SQLite | `/data/secure_vector_db.sqlite` |
| `SECURE_VECTOR_DB_API_KEY` | Clave usada para proteger los endpoints privados | `una-clave-larga-y-secreta` |
| `SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE` | Límite de solicitudes por minuto | `120` |
| `SECURE_VECTOR_DB_VECTOR_INDEX` | Backend vectorial usado por la API | `kd_tree`, `faiss`, `hnsw`, `auto` |
| `SECURE_VECTOR_DB_EMBEDDING_MODEL` | Modelo de embeddings usado internamente | `hash`, `sentence_transformers`, `auto` |
| `SECURE_VECTOR_DB_EMBEDDING_MODEL_NAME` | Nombre del modelo si se usan embeddings reales | `sentence-transformers/all-MiniLM-L6-v2` |

La variable más importante en producción o demostraciones públicas es:

```env
SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
```

Esta clave protege las operaciones privadas de la API, como insertar registros, consultar documentos, eliminar datos, buscar semánticamente y verificar integridad.

#### Despliegue local con Docker Compose

##### 1. Copiar archivo de configuración

Desde la raíz del proyecto:

```bash
cp .env.example .env
```

Luego edita `.env` y define valores adecuados.

Ejemplo recomendado:

```env
SECURE_VECTOR_DB_PATH=/data/secure_vector_db.sqlite
SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=120
SECURE_VECTOR_DB_VECTOR_INDEX=kd_tree
SECURE_VECTOR_DB_EMBEDDING_MODEL=hash
```

##### 2. Levantar el servicio

```bash
docker compose up --build
```

La API quedará disponible en:

```text
http://127.0.0.1:8000
```

La documentación interactiva estará disponible en:

```text
http://127.0.0.1:8000/docs
```

##### 3. Verificar que el servicio está activo

Ejecuta:

```bash
curl http://127.0.0.1:8000/health
```

Una respuesta esperada tiene una estructura similar a:

```json
{
  "status": "ok",
  "records": 0,
  "root_hash": "...",
  "storage": "/data/secure_vector_db.sqlite",
  "vector_index": "kd_tree",
  "embedding_model": "hash"
}
```

El endpoint `/health` es público y sirve para validar que el servicio está corriendo correctamente.

#### Persistencia con SQLite y Docker

El archivo `docker-compose.yml` monta un volumen persistente para la ruta `/data`.

Por eso, dentro de Docker se recomienda usar:

```env
SECURE_VECTOR_DB_PATH=/data/secure_vector_db.sqlite
```

Esto permite que SQLite guarde los registros fuera del ciclo de vida del contenedor. Si el contenedor se detiene o se reinicia, la base de datos sigue existiendo.

#### Prueba de persistencia

##### 1. Insertar un registro

```bash
curl -X POST http://127.0.0.1:8000/records \
  -H "Content-Type: application/json" \
  -H "X-API-Key: una-clave-larga-y-secreta" \
  -d '{"record_id":1,"text":"merkle integridad criptografica","metadata":{"topic":"crypto"}}'
```

##### 2. Detener el contenedor

```bash
docker compose down
```

##### 3. Levantar nuevamente

```bash
docker compose up
```

##### 4. Consultar el registro insertado

```bash
curl http://127.0.0.1:8000/records/1 \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

Si el registro todavía existe, la persistencia SQLite está funcionando correctamente mediante el volumen Docker.

#### Prueba de autenticación

Las rutas de datos requieren el header:

```text
X-API-Key: <tu_clave>
```

##### Petición sin clave

```bash
curl http://127.0.0.1:8000/verify
```

La API debe rechazar la solicitud porque falta la clave.

Respuesta esperada:

```json
{
  "detail": "API key inválida o ausente. Envíe el header X-API-Key."
}
```

##### Petición con clave

```bash
curl http://127.0.0.1:8000/verify \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

En este caso, la API debe responder correctamente con el estado de integridad del dataset.

#### Endpoints útiles después del despliegue

| Método | Endpoint | Autenticación | Uso |
|---|---|---|---|
| `GET` | `/health` | No | Verificar estado del servicio |
| `GET` | `/docs` | No | Abrir Swagger UI |
| `GET` | `/openapi.json` | No | Obtener especificación OpenAPI |
| `POST` | `/records` | Sí | Insertar o reemplazar documentos |
| `GET` | `/records/{record_id}` | Sí | Consultar por ID |
| `DELETE` | `/records/{record_id}` | Sí | Eliminar por ID |
| `GET` | `/range?start=1&end=5` | Sí | Consultar registros por rango |
| `GET` | `/search?q=texto&k=3` | Sí | Búsqueda semántica |
| `GET` | `/verify` | Sí | Verificar integridad Merkle |
| `POST` | `/verify/assert` | Sí | Fallar con `409 Conflict` si hay alteración |

#### Despliegue opcional en Render

El proyecto incluye una plantilla base en:

```text
deploy/render.example.yaml
```

Esta plantilla permite publicar la API como un servicio web usando Docker.

> Nota importante: Render puede usarse como despliegue cloud opcional. Sin embargo, si se desea conservar SQLite entre reinicios, se necesita un servicio con disco persistente. En planes gratuitos, la API puede servir para una demostración temporal, pero los datos SQLite pueden perderse cuando el servicio se reinicie o se redeploye.

#### Pasos generales

1. Sube el proyecto a un repositorio Git.
2. Crea un nuevo servicio web o Blueprint en Render desde ese repositorio.
3. Selecciona Docker como entorno de ejecución.
4. Usa la plantilla `deploy/render.example.yaml`.
5. Define `SECURE_VECTOR_DB_API_KEY` como variable secreta.
6. Configura la ruta de SQLite:

```env
SECURE_VECTOR_DB_PATH=/data/secure_vector_db.sqlite
```

7. Asegura que `/data` esté asociado a un disco persistente si se quiere conservar la base de datos.
8. Verifica que el servicio responda en:

```text
/health
```

9. Abre la documentación interactiva:

```text
/docs
```

#### Configuración recomendada para Render

Variables recomendadas:

```env
SECURE_VECTOR_DB_PATH=/data/secure_vector_db.sqlite
SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=120
SECURE_VECTOR_DB_VECTOR_INDEX=kd_tree
SECURE_VECTOR_DB_EMBEDDING_MODEL=hash
```

Para una demostración estable y ligera, se recomienda iniciar con:

```env
SECURE_VECTOR_DB_VECTOR_INDEX=kd_tree
SECURE_VECTOR_DB_EMBEDDING_MODEL=hash
```

Si se desea usar embeddings reales:

```env
SECURE_VECTOR_DB_EMBEDDING_MODEL=sentence_transformers
SECURE_VECTOR_DB_EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

Si se desea usar FAISS o HNSW:

```env
SECURE_VECTOR_DB_VECTOR_INDEX=faiss
```

o:

```env
SECURE_VECTOR_DB_VECTOR_INDEX=hnsw
```

En ese caso, también deben instalarse las dependencias opcionales correspondientes.

#### Prueba mínima después del despliegue cloud

Cuando el servicio ya esté publicado, reemplaza `<URL_DEL_SERVICIO>` por la URL real.

##### Health check

```bash
curl https://<URL_DEL_SERVICIO>/health
```

##### Insertar documento

```bash
curl -X POST https://<URL_DEL_SERVICIO>/records \
  -H "Content-Type: application/json" \
  -H "X-API-Key: una-clave-larga-y-secreta" \
  -d '{"record_id":10,"text":"base de datos vectorial verificable","metadata":{"topic":"database"}}'
```

##### Buscar documento por ID

```bash
curl https://<URL_DEL_SERVICIO>/records/10 \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

##### Búsqueda semántica

```bash
curl "https://<URL_DEL_SERVICIO>/search?q=integridad%20criptografica&k=3" \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

##### Verificar integridad

```bash
curl https://<URL_DEL_SERVICIO>/verify \
  -H "X-API-Key: una-clave-larga-y-secreta"
```

#### Limitación de Render Free

Si se usa **Render Free** sin disco persistente, el despliegue puede mostrar la API, Swagger y los endpoints, pero no debe usarse para demostrar persistencia real de SQLite. Para demostrar persistencia, el despliegue recomendado sigue siendo Docker Compose local con volumen persistente.


#### Limitaciones del despliegue actual

El despliegue actual es adecuado para demostración. Sin embargo, SQLite ofrece persistencia local, no una arquitectura distribuida completa. Para escenarios con alta concurrencia, replicación, tolerancia a fallos o múltiples instancias escribiendo al mismo tiempo, sería necesario extender el sistema con:

- base de datos cliente-servidor,
- replicación,
- coordinación distribuida,
- monitoreo centralizado,
- gestión avanzada de usuarios y roles,
- backups automatizados.
