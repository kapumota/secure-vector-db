### Deploy

Este directorio contiene una configuración base para publicar la API con Docker.

#### Render

1. Crea un nuevo servicio web desde el repositorio.
2. Usa `deploy/render.yaml` como blueprint.
3. Define `SECURE_VECTOR_DB_API_KEY` como variable secreta.
4. Verifica `/health` y luego abre `/docs`.

La variable `SECURE_VECTOR_DB_PATH=/data/secure_vector_db.sqlite` usa un disco persistente para que SQLite sobreviva reinicios del servicio.

#### Producción real

Para un entorno más exigente se recomienda:

- usar una clave fuerte en `SECURE_VECTOR_DB_API_KEY`
- habilitar HTTPS desde el proveedor
- activar logs centralizados
- agregar rate limiting
- monitorear latencia, memoria y tamaño de la base
- evaluar PostgreSQL u otro almacenamiento si habrá concurrencia alta.
