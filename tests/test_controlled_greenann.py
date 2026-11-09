import json
from pathlib import Path
import subprocess
import sys
import pytest

@pytest.mark.parametrize('backend', ['kd_tree', 'faiss', 'hnsw'])
def test_greenann(backend):
    root = Path(__file__).resolve().parents[1]
    p = subprocess.run([sys.executable, str(root / 'tools/controlled/greenann.py'), '--source', str(root), '--backend', backend, '--records', '6', '--queries', '3'], capture_output=True, text=True)
    if p.returncode == 2:
        pytest.skip(p.stdout)
    assert p.returncode == 0, p.stderr
    data = json.loads(p.stdout)
    assert data['status'] == 'PASS'
    assert set(data['metrics']) == {'insert', 'delete', 'search', 'open', 'verify'}
    assert data['memory']['process_peak_rss_bytes'] > 0
