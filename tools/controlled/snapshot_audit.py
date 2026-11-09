"""Auditoria offline de copias SQLite, sin reparar ni abrir el origen con el motor."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile


def backup(source, destination):
    with sqlite3.connect(Path(source).resolve().as_uri() + '?mode=ro', uri=True) as src:
        with sqlite3.connect(destination) as dst:
            src.backup(dst)


def audit(source, database, sidecar=None, backend='kd_tree'):
    sys.path.insert(0, str(Path(source).resolve()))
    from secure_vector_db.database import SecureVectorDB, SimpleMerkle
    from secure_vector_db.storage.record_store import Record
    from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore
    from secure_vector_db.crypto.incremental_merkle import hash_leaf
    checks = {}
    with tempfile.TemporaryDirectory(prefix='snapshot-audit-') as directory:
        dbcopy = Path(directory) / 'records.sqlite'
        backup(database, dbcopy)
        with sqlite3.connect(dbcopy) as conn:
            rows = conn.execute('SELECT record_id,text,metadata_json,embedding_json FROM records ORDER BY record_id').fetchall()
            meta = dict(conn.execute('SELECT key,value FROM kv_meta'))
            checks['sqlite'] = conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        records = [Record(r[0], r[1], json.loads(r[2]), json.loads(r[3])) for r in rows]
        checks['format_v2'] = meta.get('root_format_version') == '2'
        checks['primary_root'] = meta.get('root_hash') == SimpleMerkle.root_hex([r.canonical() for r in records])
        checks['recovery_marker'] = meta.get('merkle_pending') == '0'
        if sidecar is not None:
            sidecopy = Path(directory) / 'merkle.sqlite'
            backup(sidecar, sidecopy)
            store = SQLiteMerkleNodeStore(sidecopy)
            checks['merkle_nodes'] = store.verify_integrity()
            checks['merkle_records'] = store.load_leaf_digests() == {r.record_id: hash_leaf(r.canonical()).hex() for r in records}
        # Reconstruir solo en la copia. Evitar bootstrap del auxiliar original.
        key = 'SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION'
        previous = os.environ.get(key)
        os.environ[key] = 'false'
        db = None
        try:
            db = SecureVectorDB.open(dbcopy, vector_index=backend, embedding_dim=int(meta.get('embedding_dim', '8')))
            checks['id_index'] = all(db.search_by_id(r.record_id) == r for r in records)
            checks['range_index'] = db.search_by_range(0, max([r.record_id for r in records], default=0)) == records
            # Pedir todos los IDs evita exigir desempate exacto a un indice ANN.
            ids = {r.record_id for r in records}
            checks['vector_membership'] = db.vector_index.size == len(ids) and all(
                {rid for rid, _ in db.vector_index.knn(r.embedding, len(records))} == ids for r in records)
        finally:
            if db is not None:
                db.close()
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
    return {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
            'markers': meta, 'sidecar_status': 'CHECKED' if sidecar is not None else 'SKIP',
            'scope': 'Origen inactivo requerido, copias entre archivos no atomicas, formato v2'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('--source', type=Path, default=Path.cwd())
    parser.add_argument('--sidecar', type=Path)
    parser.add_argument('--backend', choices=['kd_tree', 'faiss', 'hnsw'], default='kd_tree')
    args = parser.parse_args()
    result = audit(**vars(args))
    print(json.dumps(result))
    return 0 if result['status'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
