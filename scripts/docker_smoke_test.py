"""Smoke test de contenedor para release de SecureVectorDB."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


__test__ = False


@dataclass(frozen=True)
class DockerSmokeResult:
    """Resultado del smoke test Docker."""

    status: str
    image_tag: str
    dockerfile: str
    command: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Convierte el resultado a diccionario JSON."""
        return asdict(self)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Escribe JSON estable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def docker_available() -> bool:
    """Indica si docker esta disponible."""
    return shutil.which("docker") is not None


def build_image(root: Path, dockerfile: Path, image_tag: str) -> subprocess.CompletedProcess[str]:
    """Construye imagen Docker."""
    return subprocess.run(
        ["docker", "build", "-f", str(dockerfile), "-t", image_tag, "."],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def run_container_health(image_tag: str, health_command: str) -> subprocess.CompletedProcess[str]:
    """Ejecuta comando de salud dentro del contenedor."""
    return subprocess.run(
        ["docker", "run", "--rm", image_tag, "sh", "-lc", health_command],
        capture_output=True,
        text=True,
        check=False,
    )


def run_docker_smoke_test(
    root: Path,
    dockerfile: Path,
    image_tag: str,
    health_command: str,
    output_path: Path,
    strict: bool = False,
) -> DockerSmokeResult:
    """Ejecuta smoke test Docker."""
    if not dockerfile.exists():
        result = DockerSmokeResult(
            status="failed",
            image_tag=image_tag,
            dockerfile=str(dockerfile),
            command=health_command,
            message="Dockerfile no existe",
        )
        write_json(output_path, result.to_dict())
        return result

    if not docker_available():
        result = DockerSmokeResult(
            status="tool_missing",
            image_tag=image_tag,
            dockerfile=str(dockerfile),
            command=health_command,
            message="docker no esta instalado en el entorno actual",
        )
        write_json(output_path, result.to_dict())
        return result

    build_result = build_image(root, dockerfile, image_tag)
    if build_result.returncode != 0:
        result = DockerSmokeResult(
            status="failed",
            image_tag=image_tag,
            dockerfile=str(dockerfile),
            command=health_command,
            message="fallo la construccion de imagen Docker",
        )
        write_json(
            output_path,
            {**result.to_dict(), "stdout": build_result.stdout, "stderr": build_result.stderr},
        )
        return result

    health_result = run_container_health(image_tag, health_command)
    if health_result.returncode != 0:
        result = DockerSmokeResult(
            status="failed",
            image_tag=image_tag,
            dockerfile=str(dockerfile),
            command=health_command,
            message="fallo el health check del contenedor",
        )
        write_json(
            output_path,
            {**result.to_dict(), "stdout": health_result.stdout, "stderr": health_result.stderr},
        )
        return result

    result = DockerSmokeResult(
        status="passed",
        image_tag=image_tag,
        dockerfile=str(dockerfile),
        command=health_command,
        message="contenedor construido y health check ejecutado",
    )
    write_json(output_path, result.to_dict())
    return result


def should_fail(result: DockerSmokeResult, strict: bool) -> bool:
    """Indica si el resultado debe fallar el proceso."""
    if result.status == "failed":
        return True
    if strict and result.status == "tool_missing":
        return True
    return False


def run_docker_smoke_cli(argv: list[str] | None = None) -> int:
    """Ejecuta CLI de smoke test Docker."""
    parser = argparse.ArgumentParser(description="Ejecuta smoke test Docker.")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz del proyecto.")
    parser.add_argument("--dockerfile", default="Dockerfile", help="Ruta del Dockerfile.")
    parser.add_argument("--image-tag", default="secure-vector-db:smoke", help="Tag local.")
    parser.add_argument(
        "--health-command",
        default="python -c 'import secure_vector_db; print(\"salud ok\")'",
        help="Comando ejecutado dentro del contenedor.",
    )
    parser.add_argument(
        "--output",
        default="reports/docker/docker-smoke.json",
        help="Ruta del reporte JSON.",
    )
    parser.add_argument("--strict", action="store_true", help="Falla si docker no esta disponible.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    result = run_docker_smoke_test(
        root=root,
        dockerfile=root / args.dockerfile,
        image_tag=str(args.image_tag),
        health_command=str(args.health_command),
        output_path=root / args.output,
        strict=bool(args.strict),
    )
    payload = {**result.to_dict(), "python_version": platform.python_version()}
    print(json.dumps(payload, sort_keys=True))
    return 2 if should_fail(result, bool(args.strict)) else 0


if __name__ == "__main__":
    raise SystemExit(run_docker_smoke_cli())
