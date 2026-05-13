### Despliegue

Este directorio contiene plantillas opcionales para publicar la API de **SecureVectorDB** en servicios cloud usando Docker.

El despliegue principal recomendado para la entrega del proyecto es **Docker Compose local**, porque permite ejecutar la API en un contenedor y conservar SQLite mediante un volumen persistente.

#### Despliegue principal recomendado

Desde la raíz del proyecto:

```bash
cp .env.example .env
docker compose up --build
```

La API queda disponible en:

```text
http://127.0.0.1:8000
```

La documentación interactiva queda disponible en:

```text
http://127.0.0.1:8000/docs
```

Este modo permite probar:

- estado del servicio con `/health`,
- documentación Swagger con `/docs`,
- autenticación con `X-API-Key`,
- inserción de registros,
- búsqueda por ID,
- búsqueda por rango,
- búsqueda semántica,
- verificación de integridad Merkle,
- persistencia SQLite mediante volumen Docker.

#### Render

El archivo `render.example.yaml` es una plantilla opcional para desplegar la API en Render usando Docker.

> Importante: Render Free puede servir para una demostración temporal, pero no debe considerarse el despliegue principal si se necesita persistencia SQLite. Para conservar la base de datos entre reinicios se requiere un servicio con disco persistente.

La configuración recomendada para SQLite en Render usa:

```env
SECURE_VECTOR_DB_PATH=/data/secure_vector_db.sqlite
```

La ruta `/data` debe estar asociada a un disco persistente. Si no existe disco persistente, los datos pueden perderse cuando el servicio se reinicie o se redeploye.

#### Variables principales

```env
SECURE_VECTOR_DB_PATH=/data/secure_vector_db.sqlite
SECURE_VECTOR_DB_API_KEY=una-clave-larga-y-secreta
SECURE_VECTOR_DB_RATE_LIMIT_PER_MINUTE=120
SECURE_VECTOR_DB_VECTOR_INDEX=kd_tree
SECURE_VECTOR_DB_EMBEDDING_MODEL=hash
```

#### Uso recomendado de Render

Render debe considerarse una opción opcional para:

- mostrar la API públicamente,
- probar `/health`,
- abrir `/docs`,
- demostrar endpoints con `curl`,
- validar el contenedor Docker en un entorno cloud.

Para una demostración gratuita, la API puede funcionar, pero la persistencia de SQLite no está garantizada si no se configura un disco persistente.
