"""Genera SBOM y reporte de vulnerabilidades para SecureVectorDB."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SupplyChainSummary:
    """Resumen de seguridad de supply chain."""

    sbom_status: str
    vulnerability_status: str
    component_count: int
    vulnerability_count: int
    audit_tool: str
    message: str

    def to_dict(self) -> dict[str, str | int]:
        """Convierte el resumen a diccionario JSON."""
        return asdict(self)


def read_text(path: Path) -> str:
    """Lee texto UTF-8."""
    return path.read_text(encoding="utf-8")


def detect_package_version(root: Path) -> str:
    """Detecta version declarada del paquete."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    text = read_text(pyproject)
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return match.group(1) if match else "unknown"


def normalized_purl(name: str, version: str) -> str:
    """Construye PURL basico para paquete Python."""
    package_name = name.strip().lower().replace("_", "-")
    return "pkg:pypi/" + package_name + "@" + version


def collect_installed_components() -> list[dict[str, str]]:
    """Recolecta componentes instalados del entorno Python."""
    components: list[dict[str, str]] = []
    for distribution in sorted(
        importlib.metadata.distributions(),
        key=lambda item: (item.metadata.get("Name") or "").lower(),
    ):
        name = distribution.metadata.get("Name")
        version = distribution.version
        if not name:
            continue
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": normalized_purl(name, version),
            }
        )
    return components


def build_cyclonedx_sbom(root: Path) -> dict[str, Any]:
    """Construye SBOM CycloneDX basico desde el entorno actual."""
    version = detect_package_version(root)
    components = collect_installed_components()
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": [
                {
                    "vendor": "SecureVectorDB",
                    "name": "supply_chain_security.py",
                    "version": "1",
                }
            ],
            "component": {
                "type": "application",
                "name": "secure-vector-db",
                "version": version,
            },
        },
        "components": components,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Escribe JSON estable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_vulnerability_count(payload: Any) -> int:
    """Cuenta vulnerabilidades en formatos comunes de pip-audit."""
    if isinstance(payload, dict):
        if "vulnerabilities" in payload and isinstance(payload["vulnerabilities"], list):
            return len(payload["vulnerabilities"])

        dependencies = payload.get("dependencies")
        if isinstance(dependencies, list):
            count = 0
            for dependency in dependencies:
                if isinstance(dependency, dict):
                    vulns = dependency.get("vulns") or dependency.get("vulnerabilities") or []
                    if isinstance(vulns, list):
                        count += len(vulns)
            return count

    if isinstance(payload, list):
        count = 0
        for item in payload:
            if isinstance(item, dict):
                vulns = item.get("vulns") or item.get("vulnerabilities") or []
                if isinstance(vulns, list):
                    count += len(vulns)
        return count

    return 0


def build_tool_missing_report(tool_name: str) -> dict[str, Any]:
    """Construye reporte cuando la herramienta externa no esta instalada."""
    return {
        "status": "tool_missing",
        "tool": tool_name,
        "vulnerability_count": 0,
        "message": tool_name + " no esta instalado en el entorno actual",
        "python_version": platform.python_version(),
    }


def build_skipped_audit_report() -> dict[str, Any]:
    """Construye reporte cuando el escaneo se omite de forma explicita."""
    return {
        "status": "skipped",
        "tool": "pip-audit",
        "vulnerability_count": 0,
        "message": "escaneo de vulnerabilidades omitido por configuracion",
        "python_version": platform.python_version(),
    }


def run_pip_audit(root: Path, output_path: Path) -> dict[str, Any]:
    """Ejecuta pip-audit si esta disponible."""
    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "--format",
        "json",
    ]
    result = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    raw_text = result.stdout.strip()
    if not raw_text:
        raw_text = "{}"

    try:
        raw_payload: Any = json.loads(raw_text)
    except json.JSONDecodeError:
        raw_payload = {
            "status": "error",
            "tool": "pip-audit",
            "message": "pip-audit no devolvio JSON valido",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    vulnerability_count = extract_vulnerability_count(raw_payload)
    status = "passed" if vulnerability_count == 0 else "failed"

    payload = {
        "status": status,
        "tool": "pip-audit",
        "returncode": result.returncode,
        "vulnerability_count": vulnerability_count,
        "raw": raw_payload,
        "stderr": result.stderr,
        "python_version": platform.python_version(),
    }
    write_json(output_path, payload)
    return payload


def generate_supply_chain_reports(
    root: Path,
    sbom_output: Path,
    vulnerability_output: Path,
    skip_audit: bool = False,
    require_audit_tool: bool = False,
) -> SupplyChainSummary:
    """Genera SBOM y reporte de vulnerabilidades."""
    sbom = build_cyclonedx_sbom(root)
    write_json(sbom_output, sbom)

    if skip_audit:
        vulnerability_report = build_skipped_audit_report()
        write_json(vulnerability_output, vulnerability_report)
    else:
        try:
            vulnerability_report = run_pip_audit(root, vulnerability_output)
        except (OSError, subprocess.SubprocessError):
            vulnerability_report = build_tool_missing_report("pip-audit")
            write_json(vulnerability_output, vulnerability_report)

    vulnerability_status = str(vulnerability_report.get("status", "unknown"))
    vulnerability_count = int(vulnerability_report.get("vulnerability_count", 0))

    if require_audit_tool and vulnerability_status == "tool_missing":
        vulnerability_status = "failed"

    message = "reportes de supply chain generados"
    if vulnerability_status == "tool_missing":
        message = "SBOM generado y pip-audit no instalado"
    elif vulnerability_status == "failed":
        message = "se encontraron vulnerabilidades o fallo el escaneo"

    return SupplyChainSummary(
        sbom_status="passed",
        vulnerability_status=vulnerability_status,
        component_count=len(sbom.get("components", [])),
        vulnerability_count=vulnerability_count,
        audit_tool=str(vulnerability_report.get("tool", "pip-audit")),
        message=message,
    )


def summary_has_failure(summary: SupplyChainSummary, fail_on_vulnerabilities: bool) -> bool:
    """Indica si el resumen debe fallar el gate."""
    if summary.vulnerability_status == "failed" and fail_on_vulnerabilities:
        return True
    return False


def run_supply_chain_security(argv: list[str] | None = None) -> int:
    """Ejecuta generador de reportes de supply chain."""
    parser = argparse.ArgumentParser(description="Genera SBOM y reporte de vulnerabilidades.")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz del proyecto.")
    parser.add_argument(
        "--sbom-output",
        default="reports/supply-chain/sbom.json",
        help="Ruta de salida del SBOM.",
    )
    parser.add_argument(
        "--vulnerability-output",
        default="reports/supply-chain/vulnerability-report.json",
        help="Ruta de salida del reporte de vulnerabilidades.",
    )
    parser.add_argument("--check", action="store_true", help="Ejecuta en modo gate.")
    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help="Omite pip-audit y genera reporte marcado como omitido.",
    )
    parser.add_argument(
        "--require-audit-tool",
        action="store_true",
        help="Falla si pip-audit no esta disponible.",
    )
    parser.add_argument(
        "--fail-on-vulnerabilities",
        action="store_true",
        help="Falla si el escaneo reporta vulnerabilidades.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    summary = generate_supply_chain_reports(
        root=root,
        sbom_output=root / args.sbom_output,
        vulnerability_output=root / args.vulnerability_output,
        skip_audit=bool(args.skip_audit),
        require_audit_tool=bool(args.require_audit_tool),
    )

    print(json.dumps(summary.to_dict(), sort_keys=True))

    if args.check and summary.vulnerability_status == "failed" and args.require_audit_tool:
        return 2
    if args.check and summary_has_failure(summary, bool(args.fail_on_vulnerabilities)):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run_supply_chain_security())
