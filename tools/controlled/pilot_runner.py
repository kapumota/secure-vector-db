"""Runner exploratorio AB/BA para checkouts locales identificados, sin campaña confirmatoria."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys



BASE_COMMIT = 'b18bcba268521668b1bf72314a136a2f095eee7f'
NEGATIVE_PROFILE = 'pr33-pending-merkle-v1'
SCENARIOS = tuple((phase, operation)
                  for phase in ('before_commit', 'after_commit', 'after_return', 'after_ack')
                  for operation in ('insert', 'delete'))
CHECKS = ('sqlite', 'format_v2', 'primary_root', 'recovery_marker',
          'merkle_nodes', 'merkle_records', 'id_index', 'range_index', 'vector_membership')


def build_expectations(config):
    """Resolver expectativas antes de cualquier ejecucion, nunca desde resultados."""
    if not isinstance(config, dict) or config.get('mode') != 'exploratory':
        raise ValueError('Solo se permite piloto exploratorio')
    allowed = {'mode', 'crash_audit', 'merkle', 'repeats', 'records', 'queries',
               'timeout_s', 'backend', 'variants'}
    if set(config) - allowed:
        raise ValueError('Opciones de configuracion desconocidas')
    for key in ('crash_audit', 'merkle'):
        if key in config and type(config[key]) is not bool:
            raise ValueError(f'{key} debe ser booleano')
    for key, default, minimum in (('repeats', 5, 1), ('records', 32, 2), ('queries', 16, 1)):
        value = config.get(key, default)
        if type(value) is not int or value < minimum:
            raise ValueError(f'{key} invalido')
    timeout = config.get('timeout_s', 120)
    import math
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout_s invalido')
    if config.get('backend', 'kd_tree') not in ('kd_tree', 'faiss', 'hnsw'):
        raise ValueError('Backend invalido')
    variants = config.get('variants')
    if not isinstance(variants, list) or not variants:
        raise ValueError('Se requiere una lista de variantes')
    plan = {}
    for variant in variants:
        if not isinstance(variant, dict):
            raise ValueError('Variante invalida')
        if set(variant) - {'name', 'path', 'commit', 'python', 'required', 'recovery_expectation_profile'}:
            raise ValueError('Opciones de variante desconocidas')
        if 'python' in variant and (not isinstance(variant['python'], str) or not variant['python']):
            raise ValueError('Interprete invalido')
        name = variant.get('name')
        if not isinstance(name, str) or not name.strip() or name in plan:
            raise ValueError('Nombre de variante vacio o duplicado')
        if 'required' in variant and type(variant['required']) is not bool:
            raise ValueError('required debe ser booleano')
        if 'path' not in variant:
            raise ValueError('Declarar path, usar null para variante no disponible')
        if variant['path'] is not None:
            if not isinstance(variant['path'], str) or not variant['path']:
                raise ValueError('Ruta invalida')
            import re
            if not re.fullmatch(r'[0-9a-f]{40}', variant.get('commit', '')):
                raise ValueError('Se requiere SHA completo')
        profile = variant.get('recovery_expectation_profile', 'all-pass-v1')
        if profile not in ('all-pass-v1', NEGATIVE_PROFILE):
            raise ValueError('Perfil de expectativas desconocido')
        if 'recovery_expectation_profile' in variant and not config.get('crash_audit', False):
            raise ValueError('El perfil requiere crash_audit=true')
        if profile == NEGATIVE_PROFILE and variant.get('commit') != BASE_COMMIT:
            raise ValueError('El control negativo PR33 solo corresponde al commit base')
        scenarios = []
        if config.get('crash_audit', False):
            for phase, operation in SCENARIOS:
                negative = profile == NEGATIVE_PROFILE and phase == 'after_commit'
                checks = {key: not (negative and key in ('recovery_marker', 'merkle_records'))
                          for key in CHECKS}
                scenarios.append({'phase': phase, 'operation': operation,
                                  'history_status': 'PASS', 'snapshot_status': 'FAIL' if negative else 'PASS',
                                  'snapshot_checks': checks, 'merkle_pending': '1' if negative else '0'})
        plan[name] = {'required': variant.get('required', variant['path'] is not None),
                      'profile': profile, 'scenarios': scenarios}
    return plan


def execute(command, env, timeout):
    """Conservar stdout/stderr y JSON bruto separados de su clasificacion."""
    try:
        process = subprocess.run(command, env=env, capture_output=True, text=True, timeout=timeout)
        transport = {'returncode': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr}
        try:
            raw = json.loads(process.stdout)
        except ValueError:
            raw = None
            transport['error'] = 'Salida JSON invalida'
        return raw, transport
    except (subprocess.TimeoutExpired, OSError) as exc:
        def decode(value):
            return value.decode(errors='replace') if isinstance(value, bytes) else value
        return None, {'returncode': None, 'error': str(exc),
                      'stdout': decode(getattr(exc, 'stdout', None)),
                      'stderr': decode(getattr(exc, 'stderr', None))}


def classify_scenario(item, expected):
    """Exigir la firma exacta del control, ademas de su codigo de salida."""
    history, snapshot = item.get('history'), item.get('snapshot')
    execution = item.get('execution', {})
    if not isinstance(history, dict) or not isinstance(snapshot, dict):
        return 'UNEXPECTED_FAIL'
    for label, status in (('history', expected['history_status']), ('snapshot', expected['snapshot_status'])):
        transport = execution.get(label, {})
        if transport.get('error') or transport.get('returncode') != (0 if status == 'PASS' else 1):
            return 'UNEXPECTED_FAIL'
        if item[label].get('status') != status:
            return 'UNEXPECTED_FAIL'
    checks = snapshot.get('checks')
    if (not isinstance(checks, dict) or set(checks) != set(expected['snapshot_checks'])
            or any(checks[k] is not v for k, v in expected['snapshot_checks'].items())):
        return 'UNEXPECTED_FAIL'
    if snapshot.get('sidecar_status') != 'CHECKED':
        return 'UNEXPECTED_FAIL'
    for raw in (history, snapshot):
        markers = raw.get('markers')
        if not isinstance(markers, dict) or markers.get('merkle_pending') != expected['merkle_pending']:
            return 'UNEXPECTED_FAIL'
    if ((item.get('phase'), item.get('operation')) != (expected['phase'], expected['operation'])
            or history.get('phase') != expected['phase'] or history.get('operation') != expected['operation']
            or history.get('exit_code') != 86
            or history.get('acknowledged') != (5 if expected['phase'] == 'after_ack' else 4)):
        return 'UNEXPECTED_FAIL'
    return 'EXPECTED_FAIL' if expected['snapshot_status'] == 'FAIL' else 'PASS'


def summarize(result, plan, repeats):
    """Cerrar cobertura obligatoria sin aceptar escenarios perdidos ni duplicados."""
    failed = False
    executed = 0
    negative = False
    for name, expectation in plan.items():
        entry = result['variants'][name]
        if not entry['available']:
            entry['status'] = 'SKIP'
            if expectation['required']:
                failed = True
            continue
        executed += 1
        runs, transports = entry['runs'], entry['run_execution']
        performance_ok = len(runs) == repeats and len(transports) == repeats and all(
            isinstance(row, dict) and row.get('status') == 'PASS'
            and transport.get('returncode') == 0 and not transport.get('error')
            for row, transport in zip(runs, transports))
        entry['performance_status'] = 'PASS' if performance_ok else 'UNEXPECTED_FAIL'
        actual = entry.get('crash_audits', [])
        expected = expectation['scenarios']
        coverage_ok = ([(item.get('phase'), item.get('operation')) for item in actual]
                       == [(item['phase'], item['operation']) for item in expected])
        classifications = []
        for item, target in zip(actual, expected):
            item['classification'] = classify_scenario(item, target)
            classifications.append(item['classification'])
        ok = performance_ok and coverage_ok and 'UNEXPECTED_FAIL' not in classifications
        entry['coverage_status'] = 'PASS' if coverage_ok else 'UNEXPECTED_FAIL'
        entry['status'] = ('EXPECTED_FAIL' if 'EXPECTED_FAIL' in classifications else 'PASS') if ok else 'UNEXPECTED_FAIL'
        negative |= entry['status'] == 'EXPECTED_FAIL'
        failed |= not ok
    # Una ejecucion sin variantes disponibles no acredita cobertura.
    result['status'] = 'UNEXPECTED_FAIL' if failed or not executed else 'EXPECTED_FAIL' if negative else 'PASS'
    result['exit_code'] = 1 if result['status'] == 'UNEXPECTED_FAIL' else 0
    return result


def run(config, output):
    plan = build_expectations(config)
    repeats = config.get('repeats', 5)
    variants = config['variants']
    resolved = []
    for variant in variants:
        if variant.get('path') is None:
            resolved.append((variant, None))
            continue
        path = Path(variant['path']).resolve()
        sha = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
        if sha != variant['commit']:
            raise ValueError('Commit de variante no coincide')
        if subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
            raise ValueError('La variante tiene cambios en archivos versionados')
        resolved.append((variant, path))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    encoded = json.dumps(config, sort_keys=True, indent=2)
    (output / 'config.json').write_text(encoded)
    expectation_json = json.dumps(plan, sort_keys=True, indent=2)
    (output / 'expectations.json').write_text(expectation_json)
    result = {'mode': 'exploratory', 'config_sha256': hashlib.sha256(encoded.encode()).hexdigest(),
              'expectations_sha256': hashlib.sha256(expectation_json.encode()).hexdigest(),
              'status': 'UNEXPECTED_FAIL', 'exit_code': 1,
              'variants': {v['name']: {'available': p is not None, 'run_execution': [], 'status': 'SKIP' if p is None else 'PENDING', 'reason': 'Sin implementacion local' if p is None else '', 'runs': []} for v, p in resolved}}
    env = {k: v for k, v in os.environ.items() if not k.startswith('SECURE_VECTOR_DB_')}
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONHASHSEED='0')
    env['SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION'] = 'true' if config.get('merkle', False) else 'false'
    for pair in range(repeats):
        order = resolved if pair % 2 == 0 else list(reversed(resolved))
        for variant, path in order:
            if path is None:
                continue
            command = [variant.get('python', sys.executable), str(Path(__file__).with_name('greenann.py').resolve()), '--source', str(path), '--pair', str(pair), '--backend', config.get('backend', 'kd_tree'), '--records', str(config.get('records', 32)), '--queries', str(config.get('queries', 16))]
            row, transport = execute(command, env, config.get('timeout_s', 120))
            entry = result['variants'][variant['name']]
            entry['runs'].append(row)
            entry['run_execution'].append(transport)
            (output / 'results.json').write_text(json.dumps(result, indent=2))
    # Diagnosticos separados del resultado de rendimiento, sin ocultar FAIL de integridad.
    if config.get('crash_audit', False):
        for index, (variant, path) in enumerate(resolved):
            if path is None:
                continue
            diagnostics = []
            for phase in ('before_commit', 'after_commit', 'after_return', 'after_ack'):
                for operation in ('insert', 'delete'):
                    directory = (output / f'crash-{index}-{phase}-{operation}').resolve()
                    prefix = [variant.get('python', sys.executable)]
                    scripts = Path(__file__).resolve().parent
                    commands = [
                        prefix + [str(scripts / 'crash_oracle.py'), '--source', str(path), '--directory', str(directory), '--phase', phase, '--operation', operation],
                        prefix + [str(scripts / 'snapshot_audit.py'), str(directory / 'records.sqlite'), '--source', str(path), '--sidecar', str(directory / 'merkle.sqlite'), '--backend', config.get('backend', 'kd_tree')],
                    ]
                    item = {'phase': phase, 'operation': operation, 'execution': {}}
                    for label, command in zip(('history', 'snapshot'), commands):
                        raw, transport = execute(command, env, config.get('timeout_s', 120))
                        item[label] = raw
                        item['execution'][label] = transport
                    target = plan[variant['name']]['scenarios'][len(diagnostics)]
                    item['classification'] = classify_scenario(item, target)
                    diagnostics.append(item)
                    result['variants'][variant['name']]['crash_audits'] = diagnostics
                    (output / 'results.json').write_text(json.dumps(result, indent=2))
    summarize(result, plan, repeats)
    (output / 'results.json').write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        result = run(json.loads(args.config.read_text()), args.output)
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'UNEXPECTED_FAIL', 'error': str(exc), 'exit_code': 2}))
        return 2
    print(json.dumps(result))
    return result['exit_code']

if __name__ == '__main__':
    raise SystemExit(main())
