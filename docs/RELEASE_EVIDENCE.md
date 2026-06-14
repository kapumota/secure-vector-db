### Evidence Pack y release hardening

#### Objetivo

La Fase 14.0 agrega un evidence pack reproducible para preparar el primer lanzamiento serio de SecureVectorDB.

El objetivo es que un evaluador pueda ejecutar un comando y obtener evidencia minima de seguridad, pruebas, documentacion e integridad Merkle.

#### Comando principal

```bash
make release-check
```

#### Componentes agregados

```text
scripts/release_evidence.py
docs/RELEASE_EVIDENCE.md
reports/release/release-manifest.json
```

#### Checks internos del manifest

```text
required-docs
forbidden-artifacts
env-files
merkle-evidence-line
```

#### Evidencia esperada

El manifest incluye:

```text
generated_at
python_version
package_version
git_commit
checks
reports
```

#### Alcance de Fase 14.0

Esta fase no implementa todavia SBOM ni escaneo completo de vulnerabilidades.

Eso queda para Fase 14.1.

#### Criterio de aceptacion

```text
python scripts/security_audit.py
ruff check .
mypy secure_vector_db
python -m pytest -q
python scripts/release_evidence.py --check
```

Todo debe pasar antes de abrir un release candidate.

#### Ruta posterior

```text
Fase 14.1 - SBOM y vulnerability scan
Fase 14.2 - Coverage gate y Docker smoke test
```
#### Fase 14.1 - SBOM y vulnerability scan

El evidence pack integra reportes de supply chain:

```text
reports/supply-chain/sbom.json
reports/supply-chain/vulnerability-report.json
```

El target `make supply-chain-check` genera ambos reportes. El modo estricto se ejecuta con `make supply-chain-strict`.
#### Fase 14.2 - Coverage gate y Docker smoke test

Esta seccion documenta el coverage gate y el Docker smoke test como evidencias de release.

El release-check integra gates base de cobertura y contenedor:

```text
make coverage-check
make docker-smoke-test
```

Los reportes esperados son:

```text
reports/coverage/coverage-summary.json
reports/docker/docker-smoke.json
```

Los modos estrictos son:

```text
make coverage-strict
make docker-smoke-strict
```
