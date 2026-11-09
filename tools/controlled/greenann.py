"""Medicion exploratoria, sin cambios en el motor ni estimaciones de energia."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time


def run(source, backend='kd_tree', records=32, queries=16, pair='0'):
    if records < 2 or queries < 1:
        raise ValueError('Se requieren al menos dos registros y una consulta')
    enabled = os.environ.get('SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION', 'false')
    for key in list(os.environ):
        if key.startswith('SECURE_VECTOR_DB_'):
            os.environ.pop(key)
    os.environ['SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION'] = enabled
    source = Path(source).resolve()
    sys.path.insert(0, str(source))
    from secure_vector_db.database import SecureVectorDB
    from benchmarks.benchmark import stats
    corpus = [f'documento vectorial numero {i}' for i in range(records)]
    metrics = {}

    def measure(name, operations):
        samples = []
        for operation in operations:
            start = time.perf_counter_ns()
            operation()
            samples.append((time.perf_counter_ns() - start) / 1e6)
        metrics[name] = {**stats(samples), 'samples_ms': samples,
                         'throughput_ops_s': len(samples) * 1000 / sum(samples)}

    with tempfile.TemporaryDirectory(prefix='greenann-') as directory:
        path = Path(directory) / 'records.sqlite'
        # No heredar rutas auxiliares del usuario ni mezclar bases entre ensayos.
        os.environ['SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH'] = str(Path(directory) / 'merkle.sqlite')
        db = SecureVectorDB.open(path, vector_index=backend)
        try:
            measure('insert', [lambda i=i: db.insert(i, corpus[i]) for i in range(records)])
            for i in range(min(4, queries)):
                db.semantic_search(corpus[i % records], k=1)
            measure('search', [lambda i=i: db.semantic_search(corpus[i % records], k=1) for i in range(queries)])
            measure('delete', [lambda i=i: db.delete(i) for i in range(0, records, 2)])
            def verify():
                if not db.verify_dataset():
                    raise RuntimeError('Integridad fallida')
            measure('verify', [verify])
            db.close()
            def reopen():
                nonlocal db
                db = SecureVectorDB.open(path, vector_index=backend)
            measure('open', [reopen])
            verify()
            for i in range(records):
                found = db.search_by_id(i)
                if (found is not None) != bool(i % 2):
                    raise RuntimeError('Estado inesperado tras reapertura')
            actual = db.vector_index.backend_name
        finally:
            db.close()
    versions = {}
    for name in ('numpy', 'faiss-cpu', 'hnswlib'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {'schema': 1, 'status': 'PASS', 'pair': str(pair),
            'commit': subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
            'dirty': bool(subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip()),
            'config': {'records': records, 'queries': queries, 'backend': backend, 'actual_backend': actual,
                       'corpus_sha256': hashlib.sha256('\n'.join(corpus).encode()).hexdigest(),
                       'merkle_enabled': os.getenv('SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION', 'false')},
            'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                            'host': platform.node(), 'versions': versions,
                            'threads': {k: os.getenv(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')}},
            'metrics': metrics,
            'memory': {'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
                       'scope': 'Maximo del proceso completo, incluye memoria nativa y arranque'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path.cwd())
    parser.add_argument('--backend', choices=['kd_tree', 'faiss', 'hnsw'], default='kd_tree')
    parser.add_argument('--records', type=int, default=32)
    parser.add_argument('--queries', type=int, default=16)
    parser.add_argument('--pair', default='0')
    args = parser.parse_args()
    try:
        result = run(**vars(args))
    except ImportError as exc:
        print(json.dumps({'status': 'SKIP', 'reason': str(exc)}))
        return 2
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
