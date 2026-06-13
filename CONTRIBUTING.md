### Guía de contribución

#### Flujo de ramas

Trabaja cada fase en una rama separada desde `main`.

```bash
git checkout main
git pull origin main
git checkout -b phase-x-nombre-corto
```

#### Estilo de código

- Los nombres de funciones, clases y módulos deben mantenerse en inglés.
- Los comentarios y cadenas visibles para usuarios deben escribirse en español.
- Evitar guiones largos, separadores decorativos y símbolos innecesarios.
- Mantener cambios pequeños y verificables por Pull Request.

#### Validación local

Antes de abrir un Pull Request, ejecuta:

```bash
python -m pytest -q
python benchmarks/benchmark.py --records 100 --queries 10 --json benchmark-results.json
python -m build
ruff check .
mypy secure_vector_db
```

#### Pull Request

El Pull Request debe incluir objetivo, cambios principales, validación local, riesgos y evidencia de ejecución.
