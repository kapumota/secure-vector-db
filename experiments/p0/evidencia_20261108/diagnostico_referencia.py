import json
import os
import resource
import runpy
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def measure(mode, count):
    benchmark_path = (
        Path.home()
        / "svdb-integration-p0"
        / "benchmarks"
        / "benchmark_p0_write.py"
    )

    benchmark = runpy.run_path(str(benchmark_path))

    with tempfile.TemporaryDirectory(prefix="svdb-diag-") as tmp:
        path = Path(tmp) / "records.sqlite"

        # Preparar la base antes de activar el Merkle auxiliar.
        benchmark["build_seed"](path, count)

        os.environ[
            "SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION"
        ] = "1" if mode == "on" else "0"

        db = benchmark["SecureVectorDB"].open(path)

        try:
            usage0 = resource.getrusage(resource.RUSAGE_SELF)
            cpu0 = time.process_time_ns()
            wall0 = time.perf_counter_ns()

            db.insert(count // 2, "reemplazo-p0")

            wall1 = time.perf_counter_ns()
            cpu1 = time.process_time_ns()
            usage1 = resource.getrusage(resource.RUSAGE_SELF)

            # Las verificaciones no forman parte del tiempo.
            assert db.verify_dataset()
            assert db.root_hash == db.compute_root_hash()

            if mode == "on":
                assert db.verify_merkle_integrity()

            return {
                "wall_ms": (wall1 - wall0) / 1e6,
                "cpu_ms": (cpu1 - cpu0) / 1e6,
                "voluntary_switches": (
                    usage1.ru_nvcsw - usage0.ru_nvcsw
                ),
                "involuntary_switches": (
                    usage1.ru_nivcsw - usage0.ru_nivcsw
                ),
                "input_blocks": (
                    usage1.ru_inblock - usage0.ru_inblock
                ),
                "output_blocks": (
                    usage1.ru_oublock - usage0.ru_oublock
                ),
            }

        finally:
            db.close()


def main():
    if sys.argv[1] == "child":
        result = measure(
            sys.argv[2],
            int(sys.argv[3]),
        )
        print(json.dumps(result))
        return

    out = Path(sys.argv[1])

    roots = {
        "antes": Path.home() / "secure-vector-db",
        "despues": Path.home() / "svdb-integration-p0",
    }

    cases = [
        ("off", 1000),
        ("on", 10000),
    ]

    rows = []
    output = out / "mediciones.jsonl"

    def run(variant, mode, count):
        env = os.environ.copy()
        env.pop(
            "SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION",
            None,
        )
        env["PYTHONPATH"] = str(roots[variant])

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "child",
                mode,
                str(count),
            ],
            cwd=roots[variant],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        return json.loads(result.stdout)

    with output.open("w", encoding="utf-8") as file:
        for mode, count in cases:
            print()
            print("Merkle auxiliar:", mode, flush=True)
            print("Registros:", count, flush=True)

            # Calentamiento excluido del análisis.
            for variant in roots:
                run(variant, mode, count)

            for block in range(1, 5):
                order = (
                    ["antes", "despues", "despues", "antes"]
                    if block % 2
                    else ["despues", "antes", "antes", "despues"]
                )

                for position, variant in enumerate(order, 1):
                    item = run(variant, mode, count)

                    row = {
                        "mode": mode,
                        "records": count,
                        "block": block,
                        "position": position,
                        "variant": variant,
                        **item,
                    }

                    rows.append(row)
                    file.write(json.dumps(row) + "\n")
                    file.flush()

                print(
                    "Bloque completado:",
                    block,
                    flush=True,
                )

    print()
    print("Resumen de tiempos")

    for mode, count in cases:
        print()
        print("Merkle auxiliar:", mode)
        print("Registros:", count)

        for variant in roots:
            selected = [
                row for row in rows
                if row["mode"] == mode
                and row["records"] == count
                and row["variant"] == variant
            ]

            wall = statistics.median(
                row["wall_ms"] for row in selected
            )
            cpu = statistics.median(
                row["cpu_ms"] for row in selected
            )

            switches = statistics.median(
                row["involuntary_switches"]
                for row in selected
            )

            blocks = statistics.median(
                row["output_blocks"]
                for row in selected
            )

            print()
            print("Versión:", variant)
            print("Mediana tiempo real ms:", round(wall, 2))
            print("Mediana tiempo CPU ms:", round(cpu, 2))
            print(
                "Diferencia real menos CPU ms:",
                round(wall - cpu, 2),
            )
            print(
                "Cambios de contexto involuntarios:",
                switches,
            )
            print("Bloques de salida:", blocks)

    print()
    print("Archivo de mediciones:", output)


if __name__ == "__main__":
    main()
