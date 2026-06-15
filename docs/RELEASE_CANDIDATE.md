### Release candidate v1.0.0-rc1

#### Objetivo

La Fase 17.0 prepara SecureVectorDB como release candidate versionado.

El proyecto deja de presentarse como software base inicial y pasa a documentarse como producto versionado inicial con gates reproducibles de release.

#### Version

```text
version = 1.0.0rc1
tag esperado = v1.0.0-rc1
```

#### Gates obligatorios

```bash
make release-initial-check
make release-candidate-check
```

#### Gate estricto con tag

Despues de crear el tag en HEAD:

```bash
make release-candidate-strict
```

Este target exige que el tag Git coincida con la version declarada.

#### Flujo recomendado

```bash
git checkout main
git pull origin main
git checkout -b phase-17-0-release-candidate-rc1

make release-initial-check
make release-candidate-check

git tag -a v1.0.0-rc1 -m "SecureVectorDB v1.0.0-rc1"
make release-candidate-strict
```

#### Criterio de aceptacion

```text
README no usa la frase software base inicial
pyproject.toml declara version 1.0.0rc1
VERSION coincide con pyproject.toml
docs/VERSIONING.md documenta v1.0.0-rc1
make release-candidate-check pasa
make release-candidate-strict pasa despues de crear tag
```

#### Limites

Este release candidate no publica artefactos externos.

La publicacion de paquete, firma de SBOM, provenance y release final quedan para fases posteriores.
#### Nota sobre release final v1.0.0

El release candidate `v1.0.0-rc1` queda como hito previo.

El release final activo es `v1.0.0`.
