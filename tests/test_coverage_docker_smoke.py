from __future__ import annotations

import json
from pathlib import Path

from scripts.coverage_gate import (
    CoverageGateResult,
    build_tool_missing_result,
    parse_coverage_xml,
    should_fail as should_fail_coverage,
)
from scripts.docker_smoke_test import (
    DockerSmokeResult,
    should_fail as should_fail_docker,
)


def test_parse_coverage_xml_reads_line_rate(tmp_path: Path) -> None:
    coverage_xml = tmp_path / "coverage.xml"
    coverage_xml.write_text('<coverage line-rate="0.875"></coverage>', encoding="utf-8")

    assert parse_coverage_xml(coverage_xml) == 87.5


def test_coverage_tool_missing_is_non_strict() -> None:
    result = build_tool_missing_result(80.0, Path("coverage.xml"))

    assert result.status == "tool_missing"
    assert should_fail_coverage(result, strict=False) is False
    assert should_fail_coverage(result, strict=True) is True


def test_coverage_below_threshold_only_fails_in_strict_mode() -> None:
    result = CoverageGateResult(
        status="failed",
        measured_percent=40.0,
        threshold_percent=80.0,
        tool="pytest-cov",
        report_path="coverage.xml",
        message="cobertura debajo del umbral",
    )

    assert should_fail_coverage(result, strict=False) is False
    assert should_fail_coverage(result, strict=True) is True


def test_coverage_collection_failure_always_fails() -> None:
    result = CoverageGateResult(
        status="failed",
        measured_percent=0.0,
        threshold_percent=80.0,
        tool="pytest-cov",
        report_path="coverage.xml",
        message="pytest con cobertura fallo",
    )

    assert should_fail_coverage(result, strict=False) is True


def test_docker_tool_missing_is_non_strict() -> None:
    result = DockerSmokeResult(
        status="tool_missing",
        image_tag="secure-vector-db:smoke",
        dockerfile="Dockerfile",
        command="python -c 'print(1)'",
        message="docker no esta instalado",
    )

    assert should_fail_docker(result, strict=False) is False
    assert should_fail_docker(result, strict=True) is True


def test_docker_failed_always_fails() -> None:
    result = DockerSmokeResult(
        status="failed",
        image_tag="secure-vector-db:smoke",
        dockerfile="Dockerfile",
        command="python -c 'print(1)'",
        message="fallo Docker",
    )

    assert should_fail_docker(result, strict=False) is True


def test_result_dicts_are_json_serializable() -> None:
    coverage = CoverageGateResult(
        status="passed",
        measured_percent=90.0,
        threshold_percent=80.0,
        tool="pytest-cov",
        report_path="coverage.xml",
        message="cobertura cumple el umbral",
    )
    docker = DockerSmokeResult(
        status="passed",
        image_tag="secure-vector-db:smoke",
        dockerfile="Dockerfile",
        command="python -c 'print(1)'",
        message="contenedor construido",
    )

    assert json.loads(json.dumps(coverage.to_dict()))["status"] == "passed"
    assert json.loads(json.dumps(docker.to_dict()))["status"] == "passed"
