"""Genera evidence pack de release para SecureVectorDB."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReleaseEvidenceCheck:
    """Resultado de un check de release."""

    name: str
    status: str
    message: str


@dataclass(frozen=True)
class ReleaseEvidenceManifest:
    """Manifest reproducible de evidencia de release."""

    generated_at: str
    python_version: str
    package_version: str
    git_commit: str
    checks: list[ReleaseEvidenceCheck]
    reports: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convierte el manifest a diccionario JSON."""
        payload = asdict(self)
        payload["checks"] = [asdict(check) for check in self.checks]
        return payload


def read_text(path: Path) -> str:
    """Lee texto UTF-8."""
    return path.read_text(encoding="utf-8")


def detect_package_version(root: Path) -> str:
    """Detecta version del paquete desde pyproject.toml."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"

    text = read_text(pyproject)
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if match:
        return match.group(1)
    return "unknown"


def detect_git_commit(root: Path) -> str:
    """Detecta commit actual de Git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def check_required_docs(root: Path) -> ReleaseEvidenceCheck:
    """Valida documentacion requerida para release."""
    required = [
        "README.md",
        "SECURITY.md",
        "docs/API_CONTRACT.md",
        "docs/SECURITY_BASELINE.md",
        "docs/MERKLE_AUDIT.md",
        "docs/RELEASE_EVIDENCE.md",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return ReleaseEvidenceCheck(
            name="required-docs",
            status="failed",
            message="faltan documentos: " + ", ".join(missing),
        )
    return ReleaseEvidenceCheck(
        name="required-docs",
        status="passed",
        message="documentacion requerida presente",
    )


def check_no_forbidden_artifacts(root: Path) -> ReleaseEvidenceCheck:
    """Valida que no existan artefactos temporales criticos."""
    forbidden = [
        "demo.sqlite",
        "benchmark-results.json",
    ]
    found = [name for name in forbidden if (root / name).exists()]
    if found:
        return ReleaseEvidenceCheck(
            name="forbidden-artifacts",
            status="failed",
            message="artefactos temporales encontrados: " + ", ".join(found),
        )
    return ReleaseEvidenceCheck(
        name="forbidden-artifacts",
        status="passed",
        message="no se encontraron artefactos temporales criticos",
    )


def check_no_plain_env_files(root: Path) -> ReleaseEvidenceCheck:
    """Valida que no haya archivos .env versionables en raiz."""
    found = sorted(path.name for path in root.glob(".env*") if path.is_file())
    allowed = {".env.example", ".env.sample"}
    suspicious = [name for name in found if name not in allowed]
    if suspicious:
        return ReleaseEvidenceCheck(
            name="env-files",
            status="failed",
            message="archivos env no permitidos: " + ", ".join(suspicious),
        )
    return ReleaseEvidenceCheck(
        name="env-files",
        status="passed",
        message="no se encontraron archivos env sensibles en raiz",
    )


def check_merkle_evidence_files(root: Path) -> ReleaseEvidenceCheck:
    """Valida presencia de modulos Merkle de evidencia."""
    required = [
        "secure_vector_db/crypto/incremental_merkle.py",
        "secure_vector_db/crypto/merkle_persistence.py",
        "secure_vector_db/crypto/merkle_evidence.py",
        "secure_vector_db/crypto/merkle_audit.py",
        "secure_vector_db/api/merkle_production.py",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return ReleaseEvidenceCheck(
            name="merkle-evidence-line",
            status="failed",
            message="faltan modulos Merkle: " + ", ".join(missing),
        )
    return ReleaseEvidenceCheck(
        name="merkle-evidence-line",
        status="passed",
        message="linea Merkle incremental, persistencia, evidencia y auditoria presente",
    )


def check_supply_chain_security(root: Path) -> ReleaseEvidenceCheck:
    """Valida archivos base de seguridad de supply chain."""
    required = [
        "docs/SUPPLY_CHAIN_SECURITY.md",
        "scripts/supply_chain_security.py",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return ReleaseEvidenceCheck(
            name="supply-chain-security",
            status="failed",
            message="faltan archivos de supply chain: " + ", ".join(missing),
        )
    return ReleaseEvidenceCheck(
        name="supply-chain-security",
        status="passed",
        message="configuracion de supply chain presente",
    )


def check_coverage_and_docker_tools(root: Path) -> ReleaseEvidenceCheck:
    """Valida configuracion de coverage gate y Docker smoke test."""
    required = [
        "docs/COVERAGE_AND_DOCKER_SMOKE.md",
        "scripts/coverage_gate.py",
        "scripts/docker_smoke_test.py",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return ReleaseEvidenceCheck(
            name="coverage-docker-smoke",
            status="failed",
            message="faltan archivos de coverage o Docker smoke: " + ", ".join(missing),
        )
    return ReleaseEvidenceCheck(
        name="coverage-docker-smoke",
        status="passed",
        message="coverage gate y Docker smoke test configurados",
    )


def check_merkle_write_integration(root: Path) -> ReleaseEvidenceCheck:
    """Valida integracion Merkle con escrituras reales."""
    required = [
        "docs/MERKLE_WRITE_INTEGRATION.md",
        "secure_vector_db/crypto/merkle_write_integration.py",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return ReleaseEvidenceCheck(
            name="merkle-write-integration",
            status="failed",
            message="faltan archivos de integracion Merkle: " + ", ".join(missing),
        )

    database_text = (root / "secure_vector_db" / "database.py").read_text(encoding="utf-8")
    if "_apply_merkle_write_insert" not in database_text:
        return ReleaseEvidenceCheck(
            name="merkle-write-integration",
            status="failed",
            message="database.py no conecta insert con Merkle",
        )

    return ReleaseEvidenceCheck(
        name="merkle-write-integration",
        status="passed",
        message="integracion Merkle con escrituras reales presente",
    )


def check_versioning_contract(root: Path) -> ReleaseEvidenceCheck:
    """Valida archivos base de versionado y contrato congelado."""
    required = [
        "docs/VERSIONING.md",
        "scripts/version_check.py",
        "CHANGELOG.md",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return ReleaseEvidenceCheck(
            name="versioning-contract",
            status="failed",
            message="faltan archivos de versionado: " + ", ".join(missing),
        )

    contract_text = (root / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")
    if "Fase 16.0" not in contract_text:
        return ReleaseEvidenceCheck(
            name="versioning-contract",
            status="failed",
            message="API_CONTRACT.md no contiene Fase 16.0",
        )

    return ReleaseEvidenceCheck(
        name="versioning-contract",
        status="passed",
        message="versionado y contrato congelado presentes",
    )


def check_coverage_uplift(root: Path) -> ReleaseEvidenceCheck:
    """Valida archivos de coverage uplift para release inicial."""
    required = [
        "docs/COVERAGE_UPLIFT.md",
        "tests/test_coverage_uplift_release_initial.py",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return ReleaseEvidenceCheck(
            name="coverage-uplift",
            status="failed",
            message="faltan archivos de coverage uplift: " + ", ".join(missing),
        )

    makefile_text = (root / "Makefile").read_text(encoding="utf-8")
    if "release-initial-check" not in makefile_text:
        return ReleaseEvidenceCheck(
            name="coverage-uplift",
            status="failed",
            message="Makefile no contiene release-initial-check",
        )

    return ReleaseEvidenceCheck(
        name="coverage-uplift",
        status="passed",
        message="coverage uplift para release inicial presente",
    )


def check_release_candidate_readiness(root: Path) -> ReleaseEvidenceCheck:
    """Valida que el release candidate quede documentado."""
    required = [
        "docs/RELEASE_CANDIDATE.md",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return ReleaseEvidenceCheck(
            name="release-candidate",
            status="failed",
            message="faltan archivos de release candidate: " + ", ".join(missing),
        )

    readme_text = (root / "README.md").read_text(encoding="utf-8")
    if "software base inicial" in readme_text:
        return ReleaseEvidenceCheck(
            name="release-candidate",
            status="failed",
            message="README aun usa software base inicial",
        )

    makefile_text = (root / "Makefile").read_text(encoding="utf-8")
    if "release-candidate-check" not in makefile_text:
        return ReleaseEvidenceCheck(
            name="release-candidate",
            status="failed",
            message="Makefile no contiene release-candidate-check",
        )

    return ReleaseEvidenceCheck(
        name="release-candidate",
        status="passed",
        message="release candidate v1.0.0-rc1 documentado",
    )

def check_final_release_readiness(root: Path) -> ReleaseEvidenceCheck:
    """Valida archivos de release final."""
    required = [
        "docs/RELEASE.md",
        "VERSION",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return ReleaseEvidenceCheck(
            name="final-release",
            status="failed",
            message="faltan archivos de release final: " + ", ".join(missing),
        )

    readme_text = (root / "README.md").read_text(encoding="utf-8")
    if "software base inicial" in readme_text:
        return ReleaseEvidenceCheck(
            name="final-release",
            status="failed",
            message="README aun usa software base inicial",
        )

    required_badges = [
        "badges-release-start",
        "badges-release-end",
        "actions/workflows/ci.yml/badge.svg",
        "actions/workflows/security-baseline.yml/badge.svg",
    ]
    missing_badges = [badge for badge in required_badges if badge not in readme_text]
    if missing_badges:
        return ReleaseEvidenceCheck(
            name="final-release",
            status="failed",
            message="README no contiene badges requeridos: " + ", ".join(missing_badges),
        )

    makefile_text = (root / "Makefile").read_text(encoding="utf-8")
    if "final-release-check" not in makefile_text:
        return ReleaseEvidenceCheck(
            name="final-release",
            status="failed",
            message="Makefile no contiene final-release-check",
        )

    version_text = (root / "VERSION").read_text(encoding="utf-8").strip()
    if version_text != "1.0.0":
        return ReleaseEvidenceCheck(
            name="final-release",
            status="failed",
            message="VERSION no declara 1.0.0",
        )

    return ReleaseEvidenceCheck(
        name="final-release",
        status="passed",
        message="release final v1.0.0 preparado",
    )


def collect_report_files(root: Path) -> list[str]:
    """Recolecta reportes existentes sin exigir que todos existan."""
    candidates = [
        root / "reports",
        root / "docs",
    ]
    reports: list[str] = []
    for directory in candidates:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.json")):
            reports.append(str(path.relative_to(root)))
        for path in sorted(directory.rglob("*.xml")):
            reports.append(str(path.relative_to(root)))
    return reports


def build_release_manifest(root: Path) -> ReleaseEvidenceManifest:
    """Construye manifest de evidence pack."""
    checks = [
        check_required_docs(root),
        check_no_forbidden_artifacts(root),
        check_no_plain_env_files(root),
        check_merkle_evidence_files(root),
        check_supply_chain_security(root),
        check_coverage_and_docker_tools(root),
        check_merkle_write_integration(root),
        check_versioning_contract(root),
        check_coverage_uplift(root),
        check_release_candidate_readiness(root),
        check_final_release_readiness(root),
    ]
    return ReleaseEvidenceManifest(
        generated_at=datetime.now(timezone.utc).isoformat(),
        python_version=platform.python_version(),
        package_version=detect_package_version(root),
        git_commit=detect_git_commit(root),
        checks=checks,
        reports=collect_report_files(root),
    )


def write_manifest(manifest: ReleaseEvidenceManifest, output_path: Path) -> None:
    """Escribe manifest JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def manifest_has_failures(manifest: ReleaseEvidenceManifest) -> bool:
    """Indica si el manifest tiene checks fallidos."""
    return any(check.status != "passed" for check in manifest.checks)


def run_release_evidence(argv: list[str] | None = None) -> int:
    """Ejecuta generador de evidence pack."""
    parser = argparse.ArgumentParser(description="Genera evidence pack de release.")
    parser.add_argument(
        "--root",
        default=os.getcwd(),
        help="Raiz del proyecto.",
    )
    parser.add_argument(
        "--output",
        default="reports/release/release-manifest.json",
        help="Ruta del manifest JSON.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Falla si algun check interno no pasa.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    manifest = build_release_manifest(root)
    output_path = root / args.output
    write_manifest(manifest, output_path)

    print(json.dumps(manifest.to_dict(), sort_keys=True))
    if args.check and manifest_has_failures(manifest):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run_release_evidence())
