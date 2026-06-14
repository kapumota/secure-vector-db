from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_coverage_docker_doc_mentions_phase_targets() -> None:
    text = (ROOT / "docs" / "COVERAGE_AND_DOCKER_SMOKE.md").read_text(encoding="utf-8")

    assert "Fase 14.2" in text
    assert "make coverage-check" in text
    assert "make docker-smoke-test" in text


def test_makefile_mentions_coverage_and_docker_targets() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "coverage-check" in text
    assert "docker-smoke-test" in text
    assert "scripts/coverage_gate.py" in text
    assert "scripts/docker_smoke_test.py" in text


def test_release_evidence_mentions_coverage_and_docker() -> None:
    text = (ROOT / "docs" / "RELEASE_EVIDENCE.md").read_text(encoding="utf-8")

    assert "coverage gate" in text
    assert "Docker smoke test" in text
    assert "Fase 14.2" in text


def test_security_baseline_mentions_coverage_and_docker() -> None:
    text = (ROOT / "docs" / "SECURITY_BASELINE.md").read_text(encoding="utf-8")

    assert "coverage gate" in text
    assert "Docker smoke test" in text
