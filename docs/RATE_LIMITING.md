### Redis rate limiting backend

#### Objetivo

La Fase 11 agrega una capa de backends para rate limiting.

El objetivo es mantener `MemoryRateLimiter` como backend por defecto para uso local y agregar `RedisRateLimiter` como backend distribuido opcional para despliegues con multiples procesos o multiples instancias.

#### Backends

```text
MemoryRateLimiter
RedisRateLimiter
DisabledRateLimiter
```

#### Variables de entorno

```text
SECURE_VECTOR_DB_RATE_LIMIT_BACKEND=memory
SECURE_VECTOR_DB_RATE_LIMIT_BACKEND=redis
SECURE_VECTOR_DB_RATE_LIMIT_BACKEND=disabled
SECURE_VECTOR_DB_RATE_LIMIT_REDIS_URL=redis://localhost:6379/0
SECURE_VECTOR_DB_RATE_LIMIT_MAX_REQUESTS=60
SECURE_VECTOR_DB_RATE_LIMIT_WINDOW_SECONDS=60
```

#### Backend memory

El backend en memoria sigue siendo el valor por defecto.

Es apropiado para:

```text
- demo local;
- pruebas;
- un solo proceso;
- desarrollo.
```

No es suficiente para:

```text
- multiples workers;
- multiples replicas;
- despliegues distribuidos.
```

#### Backend Redis

El backend Redis comparte contadores entre procesos e instancias.

Requiere instalar la dependencia opcional:

```bash
pip install -r requirements-redis.txt
```

Ejemplo de uso:

```bash
SECURE_VECTOR_DB_RATE_LIMIT_BACKEND=redis \
SECURE_VECTOR_DB_RATE_LIMIT_REDIS_URL=redis://localhost:6379/0 \
uvicorn secure_vector_db.api.server:app
```

#### Docker Compose opcional

```bash
docker compose -f docker-compose.redis.yml up redis
```

#### Politica de compatibilidad

Esta fase no elimina el rate limiting en memoria.

La configuracion por defecto sigue siendo `memory` para mantener compatibilidad con demos y pruebas.

#### Alcance

Esta fase no implementa cuotas por usuario, scopes, API keys por cliente ni RBAC.

La mejora se enfoca en el backend de almacenamiento de contadores de rate limit.
