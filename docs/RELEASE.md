### Release final v1.0.0

#### Objetivo

La Fase 18.0 prepara SecureVectorDB como release final `v1.0.0`.

El proyecto queda documentado como producto versionado estable inicial, con gates reproducibles y tag final.

#### Version

```text
version = 1.0.0
tag esperado = v1.0.0
```

#### Gates obligatorios

```bash
make release-initial-check
make release-candidate-check
make final-release-check
```

#### Gate estricto con tag

Despues de crear el tag en HEAD:

```bash
make final-release-strict
```

Este target exige que el tag Git coincida con la version declarada.

#### Criterio de aceptacion

```text
README contiene badges de lanzamiento
README no usa la frase software base inicial
pyproject.toml declara version 1.0.0
VERSION coincide con pyproject.toml
docs/VERSIONING.md documenta v1.0.0
make final-release-check pasa
make final-release-strict pasa despues de crear tag
```

#### Limites

Esta fase no publica artefactos en PyPI ni imagen Docker remota.

La firma de SBOM, provenance y publicacion externa quedan para fases posteriores.
