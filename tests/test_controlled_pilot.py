import pytest
from tools.controlled.pilot_runner import run

def test_absent_v3_is_skip(tmp_path):
    result = run({'mode': 'exploratory', 'variants': [{'name': 'V3', 'path': None}]}, tmp_path / 'pilot')
    assert result['variants']['V3']['status'] == 'SKIP'
    assert result['variants']['V3']['runs'] == []

def test_no_confirmatory_campaign(tmp_path):
    with pytest.raises(ValueError):
        run({'mode': 'confirmatory'}, tmp_path / 'pilot')
    assert not (tmp_path / 'pilot').exists()

def test_runner_real_checkout(tmp_path):
    from pathlib import Path
    import subprocess
    root = Path(__file__).resolve().parents[1]
    sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    # Crear una copia limpia sin modificar ramas del checkout de pruebas.
    clean = tmp_path / 'clean'
    subprocess.run(['git', 'clone', '--shared', '--no-checkout', str(root), str(clean)], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(clean), 'checkout', '--detach', sha], check=True, capture_output=True)
    config = {'mode': 'exploratory', 'repeats': 1, 'crash_audit': True, 'records': 4, 'queries': 2,
              'variants': [{'name': 'base', 'path': str(clean), 'commit': sha, 'recovery_expectation_profile': 'pr33-pending-merkle-v1'}, {'name': 'V3', 'path': None}]}
    result = run(config, tmp_path / 'pilot')
    assert result['variants']['base']['status'] == 'EXPECTED_FAIL'
    assert result['exit_code'] == 0
    assert result['variants']['base']['performance_status'] == 'PASS'
    diagnostics = result['variants']['base']['crash_audits']
    assert len(diagnostics) == 8
    assert all(d['history']['status'] == 'PASS' for d in diagnostics)
    assert all(d['snapshot']['status'] == ('FAIL' if d['phase'] == 'after_commit' else 'PASS') for d in diagnostics)
    assert result['variants']['V3']['status'] == 'SKIP'
    assert [d['classification'] for d in diagnostics].count('EXPECTED_FAIL') == 2
    assert (tmp_path / 'pilot' / 'expectations.json').is_file()
    config['variants'][0]['commit'] = '0' * 40
    with pytest.raises(ValueError): run(config, tmp_path / 'invalid')
