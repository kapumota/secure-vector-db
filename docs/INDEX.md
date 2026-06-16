### Índice de documentación técnica

Este índice organiza la documentación técnica de SecureVectorDB por nivel de importancia y por área funcional.

SecureVectorDB debe entenderse como un motor local de recuperación vectorial verificable, no como una base de datos distribuida enterprise. La documentación se ordena con esa misma idea: primero el núcleo funcional, luego seguridad, índices, integridad, release y componentes experimentales.

#### Lectura recomendada

Para una revisión rápida del proyecto:

1. [`../README.md`](../README.md): visión general, instalación, demo mínima, badges y límites.
2. [`API_CONTRACT.md`](API_CONTRACT.md): contrato público de endpoints.
3. [`CLI_CONTRACT.md`](CLI_CONTRACT.md): contrato público de comandos CLI.
4. [`STORAGE.md`](STORAGE.md): almacenamiento persistente, SQLite y límites de concurrencia.
5. [`MERKLE_EVIDENCE.md`](MERKLE_EVIDENCE.md): evidencia de integridad verificable.
6. [`SECURITY_BASELINE.md`](SECURITY_BASELINE.md): línea base de seguridad.
7. [`VERSIONING.md`](VERSIONING.md): política de versión y contrato público.

#### Documentación esencial

Estos documentos describen el comportamiento estable del proyecto.

| Documento | Propósito |
|---|---|
| [`API_CONTRACT.md`](API_CONTRACT.md) | Contrato público de endpoints, respuestas y errores de la API. |
| [`CLI_CONTRACT.md`](CLI_CONTRACT.md) | Contrato público de comandos, salidas y códigos de error de la CLI. |
| [`ERRORS.md`](ERRORS.md) | Política de errores para API, CLI y dominio interno. |
| [`STORAGE.md`](STORAGE.md) | Capa de almacenamiento, backend SQLite y límites de concurrencia. |
| [`PERSISTENCE_RECOVERY.md`](PERSISTENCE_RECOVERY.md) | Persistencia, recuperación y reconstrucción de índices. |
| [`VERSIONING.md`](VERSIONING.md) | Política de versionado y estabilidad del contrato público. |

#### Seguridad y despliegue

Estos documentos cubren autenticación, rate limiting, despliegue y cadena de suministro.

| Documento | Propósito |
|---|---|
| [`AUTH.md`](AUTH.md) | Autenticación base mediante API key. |
| [`AUTH_SCOPES.md`](AUTH_SCOPES.md) | Scopes de autorización para operaciones diferenciadas. |
| [`AUTH_JWT_EXPERIMENTAL.md`](AUTH_JWT_EXPERIMENTAL.md) | JWT experimental. No forma parte del flujo principal. |
| [`RATE_LIMITING.md`](RATE_LIMITING.md) | Limitación de tasa en memoria y backend Redis opcional. |
| [`DEPLOYMENT_SECURITY.md`](DEPLOYMENT_SECURITY.md) | Recomendaciones mínimas para despliegue seguro. |
| [`SECURITY_BASELINE.md`](SECURITY_BASELINE.md) | Línea base de seguridad para releases. |
| [`SUPPLY_CHAIN_SECURITY.md`](SUPPLY_CHAIN_SECURITY.md) | SBOM, auditoría de dependencias y seguridad de cadena de suministro. |

#### Índices, búsqueda y observabilidad

Estos documentos describen índices, planes de ejecución y extensiones experimentales.

| Documento | Propósito |
|---|---|
| [`EXPLAIN_PLAN.md`](EXPLAIN_PLAN.md) | Plan de ejecución explicado para consultas. |
| [`LEARNED_INDEXES.md`](LEARNED_INDEXES.md) | Índices aprendidos como extensión experimental. |
| [`LEARNED_INDEX_HEALTH.md`](LEARNED_INDEX_HEALTH.md) | Estado, degradación y métricas del índice aprendido. |
| [`LEARNED_INDEX_PERSISTENCE.md`](LEARNED_INDEX_PERSISTENCE.md) | Persistencia del modelo aprendido. |
| [`LEARNED_OBSERVABILITY.md`](LEARNED_OBSERVABILITY.md) | Observabilidad y benchmarks del índice aprendido. |

#### Integridad y Merkle

Estos documentos cubren evidencia criptográfica, persistencia Merkle y auditoría.

| Documento | Propósito |
|---|---|
| [`MERKLE_EVIDENCE.md`](MERKLE_EVIDENCE.md) | Exportación y verificación de evidencia Merkle. |
| [`MERKLE_INCREMENTAL.md`](MERKLE_INCREMENTAL.md) | Núcleo incremental de Merkle Tree. |
| [`MERKLE_PERSISTENCE.md`](MERKLE_PERSISTENCE.md) | Persistencia y recuperación de estado Merkle. |
| [`MERKLE_WRITE_INTEGRATION.md`](MERKLE_WRITE_INTEGRATION.md) | Integración de Merkle con escrituras. |
| [`MERKLE_AUDIT.md`](MERKLE_AUDIT.md) | Auditoría basada en evidencia Merkle. |

#### Calidad, release y mantenimiento

Estos documentos sostienen reproducibilidad, limpieza, cobertura y evidencia de release.

| Documento | Propósito |
|---|---|
| [`CLEANUP.md`](CLEANUP.md) | Limpieza local de cachés, artefactos y reportes. |
| [`COVERAGE_AND_DOCKER_SMOKE.md`](COVERAGE_AND_DOCKER_SMOKE.md) | Cobertura mínima y prueba smoke con Docker. |
| [`COVERAGE_UPLIFT.md`](COVERAGE_UPLIFT.md) | Mejora de cobertura para release inicial. |
| [`RELEASE_CANDIDATE.md`](RELEASE_CANDIDATE.md) | Evidencia del release candidate. |
| [`RELEASE.md`](RELEASE.md) | Notas del release final. |
| [`RELEASE_EVIDENCE.md`](RELEASE_EVIDENCE.md) | Evidence pack y endurecimiento de release. |

#### Documentación pública en la raíz

Estos documentos se mantienen en la raíz porque son puntos de entrada habituales del repositorio.

| Documento | Propósito |
|---|---|
| [`../README.md`](../README.md) | Portada pública del proyecto, instalación rápida, badges y límites. |
| [`../API.md`](../API.md) | Guía práctica de uso de la API. |
| [`../SECURITY.md`](../SECURITY.md) | Política pública de seguridad del repositorio. |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Guía de contribución, ramas, validación y PR. |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Registro de cambios por versión. |

#### Criterio de alcance

La documentación debe mantener una separación clara entre núcleo estable y extensiones.

| Categoría | Componentes |
|---|---|
| Núcleo estable | SQLite, CLI, API REST, API key, índices base, pruebas, Docker y evidencia Merkle. |
| Opcional | FAISS, HNSW, Redis y sentence-transformers. |
| Experimental | JWT, scopes avanzados, índices aprendidos y Merkle incremental avanzado. |
| Fuera de alcance actual | Base distribuida, clustering, replicación, consenso, sharding, multi-tenant enterprise y alta concurrencia real. |

#### Regla editorial

El README principal debe ser breve. Este índice funciona como mapa técnico. Los documentos especializados deben explicar detalles sin ampliar artificialmente el alcance del proyecto.
