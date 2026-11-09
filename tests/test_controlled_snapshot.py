from pathlib import Path
import hashlib
import sqlite3
import pytest
from tools.controlled.crash_oracle import run
from tools.controlled.snapshot_audit import audit

@pytest.mark.parametrize('phase', ['before_commit', 'after_commit', 'after_return', 'after_ack'])
def test_audit_crash_evidence(tmp_path, phase):
    root = Path(__file__).resolve().parents[1]
    directory = tmp_path / 'case'
    run(root, directory, phase)
    paths = [directory / 'records.sqlite', directory / 'merkle.sqlite']
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    result = audit(root, *paths)
    assert result['status'] == ('FAIL' if phase == 'after_commit' else 'PASS')
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]

def test_audit_detects_tampering(tmp_path):
    root = Path(__file__).resolve().parents[1]
    directory = tmp_path / 'case'
    run(root, directory, 'after_ack')
    with sqlite3.connect(directory / 'records.sqlite') as conn:
        conn.execute("UPDATE records SET text='alterado'")
    result = audit(root, directory / 'records.sqlite', directory / 'merkle.sqlite')
    assert result['checks']['primary_root'] is False
    assert result['checks']['merkle_records'] is False

@pytest.mark.parametrize('backend,module', [('faiss', 'faiss'), ('hnsw', 'hnswlib')])
def test_audit_real_ann(tmp_path, backend, module):
    pytest.importorskip(module)
    root = Path(__file__).resolve().parents[1]
    directory = tmp_path / 'case'
    run(root, directory, 'after_ack')
    assert audit(root, directory / 'records.sqlite', directory / 'merkle.sqlite', backend)['status'] == 'PASS'

def test_audit_detects_sidecar_node(tmp_path):
    root = Path(__file__).resolve().parents[1]
    directory = tmp_path / 'case'
    run(root, directory, 'after_ack')
    with sqlite3.connect(directory / 'merkle.sqlite') as conn:
        conn.execute('UPDATE merkle_nodes SET digest_hex=?', ('00' * 32,))
    assert audit(root, directory / 'records.sqlite', directory / 'merkle.sqlite')['status'] == 'FAIL'
