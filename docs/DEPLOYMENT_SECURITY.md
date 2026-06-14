### Seguridad de despliegue

#### Objetivo

Este documento define recomendaciones minimas para desplegar SecureVectorDB de forma controlada.

#### Contenedor

El contenedor debe ejecutarse con usuario no root.

Comprobacion esperada:

```bash
grep -n '^USER ' Dockerfile
```

#### Variables de entorno

La API key debe entregarse por variable de entorno o mecanismo equivalente del entorno de despliegue.

No se deben guardar claves reales en el repositorio.

#### API key

`X-API-Key` es un mecanismo simple.

Recomendacion para despliegues mas serios:

```text
- rotacion de claves;
- claves por entorno;
- revocacion;
- JWT u OAuth2 en una fase posterior;
- scopes basicos para separar lectura, escritura y administracion.
```

#### Rate limiting

El backend actual de rate limiting es en memoria.

Para multiples workers o despliegues distribuidos, se recomienda Redis en una fase posterior.

#### SQLite

SQLite es apropiado para despliegue local y demo reproducible.

Para despliegue con concurrencia alta, se recomienda preparar un backend alternativo como PostgreSQL.

#### Comandos de revision

```bash
python scripts/security_audit.py
ruff check .
mypy secure_vector_db
python -m pytest -q
```

#### Alcance

Estas recomendaciones no sustituyen una revision de seguridad externa. Sirven como baseline de release para un proyecto experimental serio.
#### Redis rate limiting opcional

Para multiples workers o replicas, configurar Redis:

```bash
SECURE_VECTOR_DB_RATE_LIMIT_BACKEND=redis
SECURE_VECTOR_DB_RATE_LIMIT_REDIS_URL=redis://localhost:6379/0
```

El archivo `docker-compose.redis.yml` levanta un Redis local para pruebas de integracion.
#### Configuracion de AuthProvider

Para despliegue local controlado:

```bash
SECURE_VECTOR_DB_AUTH_BACKEND=api_key
SECURE_VECTOR_DB_API_KEY=clave-local
```

Para rotacion simple se puede preparar una lista separada por comas:

```bash
SECURE_VECTOR_DB_API_KEYS=clave-a,clave-b
```

`SECURE_VECTOR_DB_AUTH_BACKEND=disabled` solo debe usarse en pruebas controladas.
