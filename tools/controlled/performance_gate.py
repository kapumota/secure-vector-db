"""Puerta relativa con pares, banda de incertidumbre y rechazo de datos incomparables."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import random
import statistics


def compare(baseline, candidate, tolerance=0.15, bootstrap=2000):
    if not math.isfinite(tolerance) or tolerance < 0 or bootstrap < 100:
        raise ValueError('Parametros invalidos')
    if len(baseline) != len(candidate) or len(baseline) < 5:
        raise ValueError('Se requieren al menos cinco pares completos')
    baseline = sorted(baseline, key=lambda r: r['pair'])
    candidate = sorted(candidate, key=lambda r: r['pair'])
    if len({r['pair'] for r in baseline}) != len(baseline):
        raise ValueError('Pares duplicados')
    reference = baseline[0]
    for left, right in zip(baseline, candidate):
        if left['pair'] != right['pair']:
            raise ValueError('Pares distintos')
        for row in (left, right):
            if row['status'] != 'PASS' or row['schema'] != 1:
                raise ValueError('Muestra incompleta')
            if row['config'] != reference['config'] or row['environment'] != reference['environment']:
                raise ValueError('Configuracion o entorno distintos')
    for rows in (baseline, candidate):
        if len({r['commit'] for r in rows}) != 1:
            raise ValueError('Versiones mezcladas')
    output = {}
    rng = random.Random(73)
    for metric in ('insert', 'search', 'delete', 'open', 'verify', 'rss'):
        def value(row):
            return row['memory']['process_peak_rss_bytes'] if metric == 'rss' else row['metrics'][metric]['avg_ms']
        ratios = []
        for left, right in zip(baseline, candidate):
            a, b = value(left), value(right)
            if not all(math.isfinite(v) and v > 0 for v in (a, b)):
                raise ValueError('Medicion no positiva o no finita')
            ratios.append(math.log(b / a))
        draws = sorted(math.exp(statistics.median(rng.choices(ratios, k=len(ratios)))) for _ in range(bootstrap))
        low, high = draws[int(.025 * bootstrap)], draws[int(.975 * bootstrap)]
        status = 'FAIL' if low > 1 + tolerance else 'PASS' if high <= 1 + tolerance else 'INCONCLUSIVE'
        output[metric] = {'ratio': math.exp(statistics.median(ratios)), 'ci95': [low, high], 'status': status}
    states = {v['status'] for v in output.values()}
    return {'status': 'FAIL' if 'FAIL' in states else 'INCONCLUSIVE' if 'INCONCLUSIVE' in states else 'PASS',
            'tolerance': tolerance, 'pairs': len(baseline), 'metrics': output,
            'note': 'Intervalos exploratorios por metrica, sin correccion por comparaciones multiples'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--tolerance', type=float, default=.15)
    args = parser.parse_args()
    result = compare(json.loads(args.baseline.read_text()), json.loads(args.candidate.read_text()), args.tolerance)
    print(json.dumps(result, allow_nan=False))
    return {'PASS': 0, 'FAIL': 1, 'INCONCLUSIVE': 2}[result['status']]

if __name__ == '__main__':
    raise SystemExit(main())
