### Coverage gate y Docker smoke test

#### Objetivo

La Fase 14.2 agrega dos gates de release:

```text
coverage gate
Docker smoke test
```

El objetivo es validar cobertura minima y comprobar que el artefacto de contenedor puede construirse y ejecutar un health check basico.

#### Coverage gate

El target base es:

```bash
make coverage-check
```

Genera:

```text
reports/coverage/coverage.xml
reports/coverage/coverage-summary.json
```

Si `pytest-cov` no esta instalado, el reporte queda con estado `tool_missing` y el target base no falla.

El modo base registra cobertura baja sin bloquear el release-check.
El modo estricto si bloquea cuando la cobertura queda debajo del umbral.

#### Coverage estricto

```bash
make coverage-strict
```

El modo estricto falla si falta `pytest-cov` o si la cobertura queda debajo del umbral.

#### Docker smoke test

El target base es:

```bash
make docker-smoke-test
```

Genera:

```text
reports/docker/docker-smoke.json
```

Si Docker no esta instalado, el reporte queda con estado `tool_missing` y el target base no falla.

#### Docker smoke test estricto

```bash
make docker-smoke-strict
```

El modo estricto falla si Docker no esta disponible o si el contenedor no pasa el health check.

#### Integracion con release-check

`make release-check` ejecuta los gates base:

```text
supply-chain-check
coverage-check
docker-smoke-test
release_evidence.py --check
```

#### Alcance

Esta fase no fija todavia una politica definitiva de cobertura.

El umbral inicial es 80 por ciento y puede ajustarse antes de `v1.0.0-rc1`.

#### Ruta posterior

```text
Fase 15.0 - Integracion Merkle con flujos reales de escritura
```
