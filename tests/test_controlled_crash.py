from pathlib import Path
import pytest
from tools.controlled.crash_oracle import run, replay

@pytest.mark.parametrize('phase', ['before_commit', 'after_commit', 'after_return', 'after_ack'])
@pytest.mark.parametrize('operation', ['insert', 'delete'])
def test_crash_history(tmp_path, phase, operation):
    result = run(Path(__file__).resolve().parents[1], tmp_path / 'case', phase, operation)
    assert result['status'] == 'PASS'
    assert result['acknowledged'] == (5 if phase == 'after_ack' else 4)
    assert result['markers']['merkle_pending'] == ('1' if phase == 'after_commit' else '0')

def test_replay_is_independent():
    assert replay([{'op': 'insert', 'id': 1, 'text': 'a'}, {'op': 'delete', 'id': 1}]) == {}
