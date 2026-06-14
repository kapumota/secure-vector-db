### Política de seguridad

#### Alcance

SecureVectorDB incluye autenticación por API key, rate limiting básico, persistencia SQLite y verificación de integridad con Merkle root. Estas capacidades reducen riesgos en demos y entornos controlados, pero no sustituyen un diseño enterprise completo.

#### Reporte de problemas

Para reportar una vulnerabilidad, abre un issue privado o contacta al mantenedor del repositorio con una descripción reproducible. Incluye versión, pasos de reproducción, impacto esperado y evidencia mínima.

#### Recomendaciones de despliegue

- Usar claves largas para `SECURE_VECTOR_DB_API_KEY`.
- No exponer la API sin proxy TLS en entornos públicos.
- Usar volúmenes persistentes con permisos restringidos.
- Configurar backups de SQLite si la base contiene datos importantes.
- Para despliegues con varias instancias, mover el rate limiting a Redis u otro backend compartido.

#### Limitaciones conocidas

- La autenticación por API key es simple. Para producción se recomienda OAuth2, OIDC o integración con un proveedor de identidad.
- SQLite es adecuado para persistencia local, no para coordinación distribuida de alto volumen.
- La verificación Merkle detecta alteraciones del dataset, pero no reemplaza auditoría, firmas externas ni control de acceso granular.


### Baseline de seguridad de release

#### Alcance

SecureVectorDB incluye una baseline minima de seguridad para release experimental.

La baseline cubre:

```text
- contenedor no root;
- autenticacion simple con X-API-Key;
- documentacion de limites de rate limiting en memoria;
- documentacion de SQLite como backend persistente principal;
- auditoria local con scripts/security_audit.py;
- politica de no versionar secretos.
```

#### Limites

Esta baseline no equivale a seguridad enterprise.

No incluye todavia:

```text
- OAuth2 completo;
- JWT con rotacion;
- Redis rate limiting;
- PostgreSQL como backend persistente;
- Merkle incremental;
- RBAC avanzado.
```
