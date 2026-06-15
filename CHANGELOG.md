### Registro de cambios

#### 0.7.0

- Se consolida SecureVectorDB como base vectorial verificable con SQLite, B+ Tree, índice vectorial configurable, Merkle root, API FastAPI, CLI, Docker, benchmarks y CI.
- Se alinea la versión pública del paquete con la versión expuesta por la API.
- Se documenta una base mínima para preparar futuras fases de índices aprendidos.

#### Política de versiones

- Los cambios compatibles aumentan la versión menor.
- Las correcciones internas aumentan la versión de parche.
- Los cambios incompatibles deben documentarse antes de fusionarse a `main`.
#### Fase 16.0 - API contract freeze y versionado

- Agrega `docs/VERSIONING.md`.
- Agrega `scripts/version_check.py`.
- Agrega `make version-check`.
- Agrega `make version-strict`.
- Documenta superficie estable y experimental.
#### Fase 16.1 - Coverage uplift para release inicial

- Agrega pruebas de cobertura sobre almacenamiento, indices, embeddings, CLI e integridad.
- Agrega `docs/COVERAGE_UPLIFT.md`.
- Agrega `make coverage-uplift-check`.
- Agrega `make release-initial-check`.
- Mantiene el umbral objetivo de cobertura en 80 por ciento.
#### Fase 16.1.2 - Refuerzo de cobertura para release inicial

- Agrega pruebas adicionales sobre B+ Tree, learned index, explain plan, auth, scopes, rate limit y Merkle write integration.
- Mantiene el umbral objetivo en 80 por ciento.
- No cambia contrato publico ni endpoints.
#### Fase 16.1.3 - Refuerzo final de cobertura para release inicial

- Agrega pruebas adicionales sobre LinearVectorIndex, RecordStore, store factory, embeddings y Merkle write env.
- Mantiene `coverage-strict` como criterio de release inicial.
- No cambia contrato publico ni endpoints.
#### Fase 17.0 - Release candidate v1.0.0-rc1

- Actualiza la version a `1.0.0rc1`.
- Define el tag esperado `v1.0.0-rc1`.
- Agrega `docs/RELEASE_CANDIDATE.md`.
- Agrega `make release-candidate-check`.
- Agrega `make release-candidate-strict`.
- Actualiza README para presentar el proyecto como producto versionado inicial.
