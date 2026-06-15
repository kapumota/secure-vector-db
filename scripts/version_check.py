"""Valida versionado y contrato de release para SecureVectorDB."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VersionCheckItem:
    """Resultado individual de validacion de versionado."""

    name: str
    status: str
    message: str


@dataclass(frozen=True)
class VersionCheckResult:
    """Resultado completo de validacion de versionado."""

    status: str
    package_version: str
    expected_tag: str
    git_tag: str
    checks: list[VersionCheckItem]

    def to_dict(self) -> dict[str, Any]:
        """Convierte resultado a diccionario JSON."""
        payload = asdict(self)
        payload["checks"] = [asdict(check) for check in self.checks]
        return payload


def read_text(path: Path) -> str:
    """Lee texto UTF-8."""
    return path.read_text(encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Escribe JSON estable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def detect_pyproject_version(root: Path) -> str:
    """Detecta version declarada en pyproject.toml."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return ""

    text = read_text(pyproject)
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return match.group(1) if match else ""


def detect_version_file(root: Path) -> str:
    """Detecta version declarada en archivo VERSION si existe."""
    version_file = root / "VERSION"
    if not version_file.exists():
        return ""

    return read_text(version_file).strip()


def detect_exact_git_tag(root: Path) -> str:
    """Detecta tag exacto de Git en HEAD si existe."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def expected_release_tag(version: str) -> str:
    """Calcula tag esperado para una version."""
    if not version:
        return ""

    rc_match = re.match(r"^(\d+\.\d+\.\d+)rc(\d+)$", version)
    if rc_match:
        return "v" + rc_match.group(1) + "-rc" + rc_match.group(2)

    return "v" + version


def is_semantic_version(version: str) -> bool:
    """Valida formato semver basico y prerelease PEP 440 usado por Python."""
    patterns = [
        r"^\d+\.\d+\.\d+$",
        r"^\d+\.\d+\.\d+(?:rc\d+|a\d+|b\d+)$",
        r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$",
    ]
    return any(re.match(pattern, version) for pattern in patterns)

def check_pyproject_version(version: str) -> VersionCheckItem:
    """Valida version declarada en pyproject.toml."""
    if not version:
        return VersionCheckItem(
            name="pyproject-version",
            status="failed",
            message="pyproject.toml no declara version",
        )

    if not is_semantic_version(version):
        return VersionCheckItem(
            name="pyproject-version",
            status="failed",
            message="version no cumple formato semver basico",
        )

    return VersionCheckItem(
        name="pyproject-version",
        status="passed",
        message="version declarada en pyproject.toml valida",
    )


def check_version_file(root: Path, version: str) -> VersionCheckItem:
    """Valida archivo VERSION si existe."""
    file_version = detect_version_file(root)
    if not file_version:
        return VersionCheckItem(
            name="version-file",
            status="passed",
            message="archivo VERSION ausente; pyproject.toml es fuente principal",
        )

    if file_version != version:
        return VersionCheckItem(
            name="version-file",
            status="failed",
            message="VERSION no coincide con pyproject.toml",
        )

    return VersionCheckItem(
        name="version-file",
        status="passed",
        message="VERSION coincide con pyproject.toml",
    )


def check_git_tag(root: Path, version: str, require_tag: bool) -> VersionCheckItem:
    """Valida tag Git contra version declarada."""
    tag = detect_exact_git_tag(root)
    expected = expected_release_tag(version)

    if not tag and require_tag:
        return VersionCheckItem(
            name="git-tag",
            status="failed",
            message="no existe tag exacto en HEAD",
        )

    if not tag:
        return VersionCheckItem(
            name="git-tag",
            status="passed",
            message="sin tag exacto en modo base",
        )

    accepted_tags = {version, expected, "v" + version}
    if tag not in accepted_tags:
        return VersionCheckItem(
            name="git-tag",
            status="failed",
            message="tag Git no coincide con version declarada",
        )

    return VersionCheckItem(
        name="git-tag",
        status="passed",
        message="tag Git coincide con version declarada",
    )


def check_changelog(root: Path) -> VersionCheckItem:
    """Valida presencia de CHANGELOG.md."""
    changelog = root / "CHANGELOG.md"
    if not changelog.exists():
        return VersionCheckItem(
            name="changelog",
            status="failed",
            message="CHANGELOG.md no existe",
        )

    text = read_text(changelog)
    if "Fase 16.0" not in text and "Unreleased" not in text:
        return VersionCheckItem(
            name="changelog",
            status="failed",
            message="CHANGELOG.md no contiene seccion Unreleased o Fase 16.0",
        )

    return VersionCheckItem(
        name="changelog",
        status="passed",
        message="CHANGELOG.md presente y actualizado",
    )


def check_api_contract_freeze(root: Path) -> VersionCheckItem:
    """Valida seccion de contrato estable y experimental."""
    contract = root / "docs" / "API_CONTRACT.md"
    if not contract.exists():
        return VersionCheckItem(
            name="api-contract-freeze",
            status="failed",
            message="docs/API_CONTRACT.md no existe",
        )

    text = read_text(contract)
    required = ["Fase 16.0", "estable", "experimental", "versionado"]
    missing = [item for item in required if item not in text]
    if missing:
        return VersionCheckItem(
            name="api-contract-freeze",
            status="failed",
            message="faltan marcadores de contrato: " + ", ".join(missing),
        )

    return VersionCheckItem(
        name="api-contract-freeze",
        status="passed",
        message="contrato API congelado y documentado",
    )


def build_version_check(root: Path, require_tag: bool = False) -> VersionCheckResult:
    """Construye resultado de validacion de versionado."""
    version = detect_pyproject_version(root)
    checks = [
        check_pyproject_version(version),
        check_version_file(root, version),
        check_git_tag(root, version, require_tag),
        check_changelog(root),
        check_api_contract_freeze(root),
    ]
    status = "failed" if any(check.status == "failed" for check in checks) else "passed"

    return VersionCheckResult(
        status=status,
        package_version=version,
        expected_tag=expected_release_tag(version),
        git_tag=detect_exact_git_tag(root),
        checks=checks,
    )


def run_version_check(argv: list[str] | None = None) -> int:
    """Ejecuta validador de versionado."""
    parser = argparse.ArgumentParser(description="Valida contrato API y versionado.")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz del proyecto.")
    parser.add_argument(
        "--output",
        default="reports/release/version-check.json",
        help="Ruta de salida del reporte JSON.",
    )
    parser.add_argument("--check", action="store_true", help="Falla si hay errores.")
    parser.add_argument(
        "--require-tag",
        action="store_true",
        help="Exige tag Git exacto en HEAD.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    result = build_version_check(root, require_tag=bool(args.require_tag))
    write_json(root / args.output, result.to_dict())
    print(json.dumps(result.to_dict(), sort_keys=True))

    if args.check and result.status != "passed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run_version_check())
