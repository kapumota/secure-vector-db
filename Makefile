.PHONY: clean clean-cache clean-build clean-reports clean-all

clean:
	python scripts/clean_project.py --cache --build

clean-cache:
	python scripts/clean_project.py --cache

clean-build:
	python scripts/clean_project.py --build

clean-reports:
	python scripts/clean_project.py --reports

clean-all:
	python scripts/clean_project.py --cache --build --reports
.PHONY: release-check
release-check:
	python scripts/security_audit.py
	ruff check .
	mypy secure_vector_db
	python -m pytest -q
	python scripts/release_evidence.py --check
.PHONY: supply-chain-check
supply-chain-check:
	python scripts/supply_chain_security.py --check

.PHONY: supply-chain-strict
supply-chain-strict:
	python scripts/supply_chain_security.py --check --require-audit-tool --fail-on-vulnerabilities
.PHONY: coverage-check
coverage-check:
	python scripts/coverage_gate.py --threshold 80

.PHONY: coverage-strict
coverage-strict:
	python scripts/coverage_gate.py --threshold 80 --strict

.PHONY: docker-smoke-test
docker-smoke-test:
	python scripts/docker_smoke_test.py

.PHONY: docker-smoke-strict
docker-smoke-strict:
	python scripts/docker_smoke_test.py --strict
