"""Oraculo externo de caidas de proceso, no simula perdida de energia."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

PHASES = ('before_commit', 'after_commit', 'after_return', 'after_ack')


def read_records(path):
    with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as conn:
        rows = conn.execute('SELECT record_id,text,metadata_json FROM records ORDER BY record_id').fetchall()
        meta = dict(conn.execute('SELECT key,value FROM kv_meta'))
    return {str(rid): {'text': text, 'metadata': json.loads(metadata)} for rid, text, metadata in rows}, meta


def replay(events):
    state = {}
    for event in events:
        if event['op'] == 'insert':
            state[str(event['id'])] = {'text': event['text'], 'metadata': {}}
        elif event['op'] == 'delete':
            state.pop(str(event['id']), None)
        else:
            raise ValueError('Operacion desconocida')
    return state


def worker(source, directory, phase, operation):
    sys.path.insert(0, str(Path(source).resolve()))
    from secure_vector_db.database import SecureVectorDB
    for key in list(os.environ):
        if key.startswith('SECURE_VECTOR_DB_'):
            os.environ.pop(key)
    os.environ['SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION'] = 'true'
    os.environ['SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH'] = str(Path(directory) / 'merkle.sqlite')
    db = SecureVectorDB.open(Path(directory) / 'records.sqlite')
    events = [{'op': 'insert', 'id': 1, 'text': 'primero'},
              {'op': 'insert', 'id': 1, 'text': 'reemplazo'},
              {'op': 'insert', 'id': 2, 'text': 'segundo'},
              {'op': 'delete', 'id': 2}]
    target = {'op': operation, 'id': 1, 'text': 'ultimo'}
    def apply(event):
        if event['op'] == 'insert':
            db.insert(event['id'], event['text'])
        else:
            db.delete(event['id'])
    def acknowledge(event):
        print(json.dumps(event), flush=True)
        if sys.stdin.readline().strip() != 'continue':
            raise RuntimeError('Falta confirmacion del padre')
    for event in events:
        apply(event)
        acknowledge(event)
    original = db._durable.commit_record_and_root
    def interrupted(**kwargs):
        if phase == 'before_commit':
            os._exit(86)
        result = original(**kwargs)
        if phase == 'after_commit':
            os._exit(86)
        return result
    db._durable.commit_record_and_root = interrupted
    apply(target)
    if phase == 'after_return':
        os._exit(86)
    acknowledge(target)
    os._exit(86)


def run(source, directory, phase='after_commit', operation='insert', timeout=30):
    if phase not in PHASES or operation not in ('insert', 'delete'):
        raise ValueError('Escenario desconocido')
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--source', str(Path(source).resolve()), '--directory', str(directory), '--phase', phase, '--operation', operation]
    # Archivo stderr evita bloquear la tuberia si el hijo informa un error extenso.
    with (directory / 'stderr.log').open('w') as errors, (directory / 'history.jsonl').open('x') as journal:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True)
        import threading
        timer = threading.Timer(timeout, process.kill)
        timer.start()
        events = []
        try:
            for line in process.stdout:
                event = json.loads(line)
                journal.write(json.dumps(event) + '\n')
                journal.flush()
                os.fsync(journal.fileno())
                events.append(event)
                process.stdin.write('continue\n')
                process.stdin.flush()
            code = process.wait(timeout=timeout)
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdin.close()
            process.stdout.close()
    if code != 86:
        raise RuntimeError(f'Caida no controlada: {code}, consultar stderr.log')
    actual, meta = read_records(directory / 'records.sqlite')
    # Releer la evidencia durable del padre, no el estado del motor.
    events = [json.loads(line) for line in (directory / 'history.jsonl').read_text().splitlines()]
    target = {'op': operation, 'id': 1, 'text': 'ultimo'}
    confirmed = replay(events)
    allowed = [confirmed] if phase == 'after_ack' else [confirmed, replay(events + [target])]
    result = {'status': 'PASS' if actual in allowed else 'FAIL', 'phase': phase,
              'operation': operation, 'exit_code': code, 'acknowledged': len(events),
              'allowed_states': allowed, 'actual': actual, 'markers': meta,
              'scope': 'Conformidad del historial, integridad se evalua por SnapshotAudit'}
    (directory / 'result.json').write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path.cwd())
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--phase', choices=PHASES, default='after_commit')
    parser.add_argument('--operation', choices=['insert', 'delete'], default='insert')
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        worker(args.source, args.directory, args.phase, args.operation)
    else:
        result = run(args.source, args.directory, args.phase, args.operation)
        print(json.dumps(result))
        return 0 if result['status'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
