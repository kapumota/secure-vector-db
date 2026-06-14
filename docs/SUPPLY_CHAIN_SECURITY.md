### SBOM y vulnerability scan

#### Objetivo

La Fase 14.1 agrega evidencia de seguridad de supply chain para SecureVectorDB.

El objetivo es generar un SBOM y un reporte de vulnerabilidades como parte del flujo de release.

#### Componentes agregados

```text
scripts/supply_chain_security.py
reports/supply-chain/sbom.json
reports/supply-chain/vulnerability-report.json
```

#### SBOM

El SBOM se genera en formato compatible con CycloneDX.

```text
bomFormat
specVersion
metadata
components
purl
```

#### Vulnerability scan

El escaneo usa `pip-audit` si esta disponible en el entorno.

Si `pip-audit` no esta instalado, el reporte se genera con estado `tool_missing`. Esto permite introducir la fase sin romper entornos existentes.

#### Modo estricto

Para exigir la herramienta externa:

```bash
python scripts/supply_chain_security.py --check --require-audit-tool
```

Para fallar si aparecen vulnerabilidades:

```bash
python scripts/supply_chain_security.py --check --fail-on-vulnerabilities
```

#### Make targets

```bash
make supply-chain-check
make supply-chain-strict
```

#### Relacion con release-check

`make release-check` ejecuta `make supply-chain-check` antes de generar el manifest de release.

#### Alcance

Esta fase no fija todavia una politica de excepciones CVE.

Esa politica debe agregarse cuando el proyecto defina versiones congeladas para `v1.0.0-rc1`.

#### Ruta posterior

```text
Fase 14.2 - Coverage gate y Docker smoke test
```
