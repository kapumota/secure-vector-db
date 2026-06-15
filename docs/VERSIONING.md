### Versionado y API contract freeze

#### Objetivo

La Fase 16.0 congela el contrato publico de SecureVectorDB antes del release candidate.

El objetivo es separar claramente lo estable de lo experimental y validar que la version declarada sea consistente.

#### Fuente principal de version

La fuente principal de version es:

```text
pyproject.toml
```

Si existe archivo `VERSION`, debe coincidir con `pyproject.toml`.

#### Tag esperado

Para una version `X.Y.Z`, el tag recomendado es:

```text
vX.Y.Z
```

Ejemplo:

```text
version = 0.7.0
tag esperado = v0.7.0
```

#### Validacion base

```bash
make version-check
```

El modo base valida:

```text
pyproject.toml
VERSION si existe
CHANGELOG.md
docs/API_CONTRACT.md
formato semver
```

No exige tag Git exacto en HEAD.

#### Validacion estricta

```bash
make version-strict
```

El modo estricto exige que HEAD tenga un tag compatible con la version declarada.

Este modo debe usarse para release candidate y release final.

#### Contrato estable

Para el primer release, se considera estable:

```text
storage SQLite
API key
scopes read/write/admin
rate limiting memory
evidence pack
supply chain check base
coverage check base
Docker smoke test base
Merkle write integration opt-in
```

#### Contrato experimental

Se considera experimental:

```text
JWT
Redis rate limiting
Merkle production API
learned index
coverage strict
docker smoke strict
version strict
```

#### Politica de cambios

Un cambio incompatible en contrato estable requiere version mayor.

Un cambio en contrato experimental puede cambiar antes de estabilizarse, pero debe estar documentado.

#### Ruta posterior

```text
Fase 16.1 - Coverage uplift para release candidate
Fase 17.0 - Release candidate v1.0.0-rc1
```
#### Cobertura para release inicial

La Fase 16.1 exige que `make coverage-strict` pase antes del release candidate.

El target recomendado para validar el estado previo al release inicial es:

```text
make release-initial-check
```
#### Release final v1.0.0

La version declarada para el release final es:

```text
1.0.0
```

El tag Git recomendado es:

```text
v1.0.0
```

El modo base valida archivos y contrato:

```text
make final-release-check
```

El modo estricto exige tag exacto en HEAD:

```text
make final-release-strict
```
