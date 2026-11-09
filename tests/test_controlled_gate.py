from copy import deepcopy
import pytest
from tools.controlled.performance_gate import compare

def rows(factor=1):
    return [dict(schema=1, status='PASS', pair=str(i), commit='a', config={}, environment={}, memory={'process_peak_rss_bytes': 100 * factor}, metrics={k: {'avg_ms': factor} for k in ('insert', 'search', 'delete', 'open', 'verify')}) for i in range(5)]

def test_gate_detects_relative_regression():
    assert compare(rows(), rows())['status'] == 'PASS'
    assert compare(rows(), rows(2))['status'] == 'FAIL'

def test_gate_rejects_incomparable_and_missing():
    bad = deepcopy(rows())
    bad[0]['environment'] = {'host': 'otro'}
    with pytest.raises(ValueError): compare(rows(), bad)
    with pytest.raises(ValueError): compare(rows()[:2], rows()[:2])
    with pytest.raises(ValueError): compare(rows(), rows(0))

def test_gate_inconclusive_and_duplicate_pairs():
    candidate = rows()
    for i, row in enumerate(candidate):
        for metric in row['metrics'].values():
            metric['avg_ms'] = 0.5 if i < 2 else 2
    assert compare(rows(), candidate)['status'] == 'INCONCLUSIVE'
    candidate[1]['pair'] = candidate[0]['pair']
    with pytest.raises(ValueError): compare(rows(), candidate)
