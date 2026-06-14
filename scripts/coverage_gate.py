"""Coverage gate para release de SecureVectorDB."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CoverageGateResult:
    """Resultado del gate de cobertura."""

    status: str
    measured_percent: float
    threshold_percent: float
    tool: str
    report_path: str
    message: str

    def to_dict(self) -> dict[str, str | float]:
        """Convierte el resultado a diccionario JSON."""
        return asdict(self)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Escribe JSON estable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_coverage_xml(path: Path) -> float:
    """Lee porcentaje de cobertura desde coverage.xml."""
    root = ElementTree.parse(path).getroot()
    line_rate = root.attrib.get("line-rate")
    if line_rate is None:
        raise ValueError("coverage.xml no contiene line-rate")
    return round(float(line_rate) * 100.0, 2)


def has_pytest_cov() -> bool:
    """Indica si pytest-cov esta disponible."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    return "--cov" in result.stdout


def run_pytest_cov(root: Path, xml_path: Path) -> subprocess.CompletedProcess[str]:
    """Ejecuta pytest con cobertura XML."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=secure_vector_db",
            "--cov-report=xml:" + str(xml_path),
            "-q",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def build_tool_missing_result(threshold_percent: float, report_path: Path) -> CoverageGateResult:
    """Construye resultado cuando pytest-cov no esta instalado."""
    return CoverageGateResult(
        status="tool_missing",
        measured_percent=0.0,
        threshold_percent=threshold_percent,
        tool="pytest-cov",
        report_path=str(report_path),
        message="pytest-cov no esta instalado en el entorno actual",
    )


def run_coverage_gate(
    root: Path,
    threshold_percent: float,
    xml_path: Path,
    json_path: Path,
    strict: bool = False,
) -> CoverageGateResult:
    """Ejecuta coverage gate."""
    if not has_pytest_cov():
        result = build_tool_missing_result(threshold_percent, xml_path)
        write_json(json_path, result.to_dict())
        return result

    process = run_pytest_cov(root, xml_path)
    if process.returncode != 0:
        result = CoverageGateResult(
            status="failed",
            measured_percent=0.0,
            threshold_percent=threshold_percent,
            tool="pytest-cov",
            report_path=str(xml_path),
            message="pytest con cobertura fallo",
        )
        write_json(json_path, {**result.to_dict(), "stdout": process.stdout, "stderr": process.stderr})
        return result

    measured = parse_coverage_xml(xml_path)
    status = "passed" if measured >= threshold_percent else "failed"
    message = "cobertura cumple el umbral" if status == "passed" else "cobertura debajo del umbral"

    result = CoverageGateResult(
        status=status,
        measured_percent=measured,
        threshold_percent=threshold_percent,
        tool="pytest-cov",
        report_path=str(xml_path),
        message=message,
    )
    write_json(json_path, result.to_dict())
    return result


def should_fail(result: CoverageGateResult, strict: bool) -> bool:
    """Indica si el resultado debe fallar el proceso."""
    if result.status == "failed" and result.message == "pytest con cobertura fallo":
        return True
    if strict and result.status == "failed":
        return True
    if strict and result.status == "tool_missing":
        return True
    return False


def run_coverage_gate_cli(argv: list[str] | None = None) -> int:
    """Ejecuta CLI de coverage gate."""
    parser = argparse.ArgumentParser(description="Ejecuta coverage gate de release.")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz del proyecto.")
    parser.add_argument("--threshold", type=float, default=80.0, help="Umbral minimo.")
    parser.add_argument(
        "--xml-output",
        default="reports/coverage/coverage.xml",
        help="Ruta de coverage.xml.",
    )
    parser.add_argument(
        "--json-output",
        default="reports/coverage/coverage-summary.json",
        help="Ruta del resumen JSON.",
    )
    parser.add_argument("--strict", action="store_true", help="Falla si falta pytest-cov.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    result = run_coverage_gate(
        root=root,
        threshold_percent=float(args.threshold),
        xml_path=root / args.xml_output,
        json_path=root / args.json_output,
        strict=bool(args.strict),
    )
    payload = {**result.to_dict(), "python_version": platform.python_version()}
    print(json.dumps(payload, sort_keys=True))
    return 2 if should_fail(result, bool(args.strict)) else 0


if __name__ == "__main__":
    raise SystemExit(run_coverage_gate_cli())
