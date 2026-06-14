#!/usr/bin/env python3
# Ejecuta el generador de SBOM y reporte de vulnerabilidades.

from scripts.supply_chain_security import run_supply_chain_security


if __name__ == "__main__":
    raise SystemExit(run_supply_chain_security())
