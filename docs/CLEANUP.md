### Limpieza local

#### Objetivo

La limpieza local evita que caches, artefactos de build y reportes generados ensucien los Pull Requests.

#### Comandos

```bash
make clean
make clean-cache
make clean-build
make clean-reports
make clean-all
```

#### Alcance

`make clean` elimina caches y artefactos de build. No elimina `.secure_db`, porque ese directorio corresponde al entorno virtual local.

`make clean-reports` elimina reportes generados localmente, como `benchmark-results.json` y archivos JSON o CSV dentro de `reports/`.

#### Uso recomendado antes de un commit

```bash
make clean
ruff check .
mypy secure_vector_db
python -m pytest -q
git status --short --ignored | head -80
```
