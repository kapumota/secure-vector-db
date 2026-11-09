"""Controles adversariales de clasificacion, conservando evidencia bruta."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from tools.controlled.pilot_runner import (
    BASE_COMMIT, NEGATIVE_PROFILE, build_expectations, classify_scenario,
    execute, summarize, main, run,
)


def config(profile=NEGATIVE_PROFILE):
    return {'mode': 'exploratory', 'crash_audit': True, 'repeats': 1,
            'variants': [{'name': 'base', 'path': '/tmp/base', 'commit': BASE_COMMIT,
                          'recovery_expectation_profile': profile},
                         {'name': 'V3', 'path': None}]}


def item_for(target):
    return {'phase': target['phase'], 'operation': target['operation'],
            'history': {'status': 'PASS', 'phase': target['phase'], 'operation': target['operation'],
                        'exit_code': 86, 'acknowledged': 5 if target['phase'] == 'after_ack' else 4,
                        'markers': {'merkle_pending': target['merkle_pending']}},
            'snapshot': {'status': target['snapshot_status'], 'checks': dict(target['snapshot_checks']),
                         'sidecar_status': 'CHECKED', 'markers': {'merkle_pending': target['merkle_pending']}},
            'execution': {'history': {'returncode': 0},
                          'snapshot': {'returncode': 1 if target['snapshot_status'] == 'FAIL' else 0}}}


def fixture_result(plan):
    return {'variants': {'base': {'available': True, 'runs': [{'status': 'PASS'}],
                                  'run_execution': [{'returncode': 0}],
                                  'crash_audits': [item_for(t) for t in plan['base']['scenarios']]},
                         'V3': {'available': False, 'runs': []}}}


def test_explicit_plan_and_raw_preservation():
    plan = build_expectations(config())
    for target in plan['base']['scenarios']:
        item = item_for(target)
        original = deepcopy(item)
        assert classify_scenario(item, target) == ('EXPECTED_FAIL' if target['phase'] == 'after_commit' else 'PASS')
        assert item == original
    result = summarize(fixture_result(plan), plan, 1)
    assert result['status'] == 'EXPECTED_FAIL' and result['exit_code'] == 0
    assert result['variants']['V3']['status'] == 'SKIP'


def test_no_profile_never_accepts_observed_failure():
    negative = build_expectations(config())['base']['scenarios'][2]
    strict_config = config()
    strict_config['variants'][0].pop('recovery_expectation_profile')
    expected = build_expectations(strict_config)['base']['scenarios'][2]
    assert classify_scenario(item_for(negative), expected) == 'UNEXPECTED_FAIL'


@pytest.mark.parametrize('mutation', ['primary_root', 'merkle_nodes', 'sqlite', 'missing_check',
                                     'extra_check', 'numeric_bool', 'unexpected_pass', 'history_fail',
                                     'marker', 'missing_auxiliary', 'exit_error', 'execution_error',
                                     'missing_history', 'wrong_phase', 'missing_ack'])
def test_fail_is_not_a_blanket_exception(mutation):
    target = build_expectations(config())['base']['scenarios'][2]
    item = item_for(target)
    if mutation in ('primary_root', 'merkle_nodes', 'sqlite'):
        item['snapshot']['checks'][mutation] = False
    elif mutation == 'missing_check': del item['snapshot']['checks']['sqlite']
    elif mutation == 'extra_check': item['snapshot']['checks']['unknown'] = True
    elif mutation == 'numeric_bool': item['snapshot']['checks']['sqlite'] = 1
    elif mutation == 'unexpected_pass': item['snapshot']['status'] = 'PASS'
    elif mutation == 'history_fail': item['history']['status'] = 'FAIL'
    elif mutation == 'marker': item['snapshot']['markers']['merkle_pending'] = '0'
    elif mutation == 'missing_auxiliary': item['snapshot']['sidecar_status'] = 'SKIP'
    elif mutation == 'exit_error': item['execution']['snapshot']['returncode'] = 2
    elif mutation == 'execution_error': item['execution']['snapshot']['error'] = 'timeout'
    elif mutation == 'missing_history': item['history'] = None
    elif mutation == 'wrong_phase': item['phase'] = 'after_ack'
    elif mutation == 'missing_ack': item['history']['acknowledged'] = 3
    assert classify_scenario(item, target) == 'UNEXPECTED_FAIL'


@pytest.mark.parametrize('missing', ['scenario', 'duplicate', 'performance', 'backend', 'required_variant', 'all_skipped'])
def test_coverage_loss_nonzero(missing):
    plan = build_expectations(config())
    result = fixture_result(plan)
    base = result['variants']['base']
    if missing == 'scenario': base['crash_audits'].pop()
    elif missing == 'duplicate': base['crash_audits'][1] = deepcopy(base['crash_audits'][0])
    elif missing == 'performance': base['runs'].clear()
    elif missing == 'backend':
        base['runs'][0]['status'] = 'SKIP'
        base['run_execution'][0]['returncode'] = 2
    elif missing == 'required_variant':
        result['variants']['V3']['available'] = False
        plan['V3']['required'] = True
    else:
        base['available'] = False
        plan['base']['required'] = False
    assert summarize(result, plan, 1)['exit_code'] != 0


@pytest.mark.parametrize('change', ['profile', 'commit', 'disabled', 'boolean', 'repeats', 'timeout', 'backend'])
def test_invalid_configuration_rejected_before_execution(change, tmp_path, monkeypatch):
    cfg = config()
    if change == 'profile': cfg['variants'][0]['recovery_expectation_profile'] = 'aceptar-todo'
    elif change == 'commit': cfg['variants'][0]['commit'] = 'a' * 40
    elif change == 'disabled': cfg['crash_audit'] = False
    elif change == 'boolean': cfg['crash_audit'] = 'true'
    elif change == 'repeats': cfg['repeats'] = True
    elif change == 'timeout': cfg['timeout_s'] = float('nan')
    else: cfg['backend'] = 'inexistente'
    def forbidden(*args, **kwargs):
        pytest.fail('Se ejecuto un proceso con configuracion invalida')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    with pytest.raises(ValueError): run(cfg, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_execution_preserves_raw_and_failure_transport(monkeypatch):
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess([], 9, '{"status":"FAIL"}', 'error'))
    raw, transport = execute([], {}, 1)
    assert raw == {'status': 'FAIL'} and transport['returncode'] == 9
    assert transport['stdout'] == '{"status":"FAIL"}' and transport['stderr'] == 'error'
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess([], 0, 'no-json', ''))
    assert execute([], {}, 1)[1]['error']
    def timeout(*a, **k): raise subprocess.TimeoutExpired('x', 1, output=b'parcial')
    monkeypatch.setattr(subprocess, 'run', timeout)
    assert execute([], {}, 1)[1]['stdout'] == 'parcial'
    def absent(*a, **k): raise FileNotFoundError('interprete inexistente')
    monkeypatch.setattr(subprocess, 'run', absent)
    assert execute([], {}, 1)[1]['error']


def test_cli_invalid_config_nonzero(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'config.json'
    path.write_text('{"mode":"confirmatory"}')
    monkeypatch.setattr(sys, 'argv', ['pilot_runner', str(path), str(tmp_path / 'output')])
    assert main() == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'UNEXPECTED_FAIL'


def test_all_pass_profile_and_plan_written_before_execution(tmp_path, monkeypatch):
    import hashlib
    import tools.controlled.pilot_runner as runner
    cfg = config('all-pass-v1')
    output = tmp_path / 'pilot'
    # La resolucion Git es independiente del proceso de medicion simulado.
    monkeypatch.setattr(subprocess, 'check_output', lambda command, **kwargs: BASE_COMMIT + '\n' if 'rev-parse' in command else '')
    expected = build_expectations(cfg)
    called = []
    def execute_checked(command, env, timeout):
        assert json.loads((output / 'expectations.json').read_text()) == expected
        assert (output / 'config.json').is_file()
        called.append(command)
        if 'greenann.py' in command[1]:
            return {'status': 'PASS'}, {'returncode': 0, 'stdout': '{"status":"PASS"}', 'stderr': ''}
        if 'crash_oracle.py' in command[1]:
            phase = command[command.index('--phase') + 1]
            operation = command[command.index('--operation') + 1]
            target = next(t for t in expected['base']['scenarios'] if (t['phase'], t['operation']) == (phase, operation))
            execute_checked.current = item_for(target)
            return execute_checked.current['history'], {'returncode': 0}
        return execute_checked.current['snapshot'], {'returncode': 0}
    monkeypatch.setattr(runner, 'execute', execute_checked)
    result = run(cfg, output)
    assert len(called) == 17
    assert result['status'] == 'PASS' and result['exit_code'] == 0
    assert result['expectations_sha256'] == hashlib.sha256((output / 'expectations.json').read_bytes()).hexdigest()


def test_unknown_option_is_invalid():
    cfg = config()
    cfg['variants'][0]['accept_failures'] = True
    with pytest.raises(ValueError): build_expectations(cfg)
