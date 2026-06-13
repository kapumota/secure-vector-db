#!/usr/bin/env python3
# Limpia caches y artefactos locales del proyecto.

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


CACHE_DIRS = (
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
)

BUILD_DIRS = (
    "build",
    "dist",
)

BUILD_GLOBS = (
    "*.egg-info",
)

REPORT_FILES = (
    "benchmark-results.json",
)

REPORT_GLOBS = (
    "reports/*.json",
    "reports/*.csv",
)

SKIP_DIRS = (
    ".git",
    ".secure_db",
    ".venv",
    "venv",
    "env",
    "vector",
)


def should_skip(path: Path, root: Path) -> bool:
    # Evita recorrer entornos virtuales y metadatos de Git.
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True

    return any(part in SKIP_DIRS for part in relative.parts)


def iter_matching_paths(root: Path, pattern: str):
    # Itera rutas coincidentes sin entrar a entornos locales.
    for path in root.glob(pattern):
        if should_skip(path, root):
            continue
        yield path


def remove_path(path: Path) -> bool:
    # Elimina un archivo o directorio si existe.
    if not path.exists():
        return False

    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    print(f"Eliminado: {path}")
    return True


def remove_glob(root: Path, pattern: str) -> int:
    # Elimina rutas que coinciden con un patron.
    removed = 0
    for path in iter_matching_paths(root, pattern):
        if remove_path(path):
            removed += 1
    return removed


def clean_cache(root: Path) -> int:
    # Limpia caches de herramientas Python sin tocar entornos virtuales.
    removed = 0
    for name in CACHE_DIRS:
        removed += int(remove_path(root / name))

    removed += remove_glob(root, "**/__pycache__")
    removed += remove_glob(root, "**/*.pyc")
    removed += remove_glob(root, "**/*.pyo")
    removed += int(remove_path(root / ".coverage"))
    return removed


def clean_build(root: Path) -> int:
    # Limpia artefactos de empaquetado.
    removed = 0
    for name in BUILD_DIRS:
        removed += int(remove_path(root / name))
    for pattern in BUILD_GLOBS:
        removed += remove_glob(root, pattern)
    return removed


def clean_reports(root: Path) -> int:
    # Limpia reportes generados localmente.
    removed = 0
    for name in REPORT_FILES:
        removed += int(remove_path(root / name))
    for pattern in REPORT_GLOBS:
        removed += remove_glob(root, pattern)
    return removed


def parse_args() -> argparse.Namespace:
    # Construye los argumentos de linea de comandos.
    parser = argparse.ArgumentParser(
        description="Limpia caches y artefactos locales de SecureVectorDB."
    )
    parser.add_argument("--cache", action="store_true", help="Limpia caches locales.")
    parser.add_argument("--build", action="store_true", help="Limpia artefactos de build.")
    parser.add_argument("--reports", action="store_true", help="Limpia reportes generados.")
    return parser.parse_args()


def main() -> None:
    # Ejecuta la limpieza solicitada.
    args = parse_args()
    root = Path(__file__).resolve().parents[1]

    if not any((args.cache, args.build, args.reports)):
        args.cache = True
        args.build = True

    removed = 0
    if args.cache:
        removed += clean_cache(root)
    if args.build:
        removed += clean_build(root)
    if args.reports:
        removed += clean_reports(root)

    print(f"Limpieza completada. Elementos eliminados: {removed}")


if __name__ == "__main__":
    main()
