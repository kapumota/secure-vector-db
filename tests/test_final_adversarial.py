"""Regresiones del cierre adversarial."""
import random
import json
import pytest
from secure_vector_db.database import SecureVectorDB
from secure_vector_db.errors import ValidationError
from secure_vector_db.indexes.bplus_tree import BPlusTree
from secure_vector_db.indexes.kd_tree_vector_index import KDTreeVectorIndex
from secure_vector_db.api.auth_jwt import JwtAuthProvider, create_hs256_jwt, _b64url_encode

@pytest.mark.parametrize('order', [3, 4, 5, 7, 8])
def test_mixed_tree_matches_dictionary(order):
    for seed in range(10):
        rng = random.Random(seed)
        tree = BPlusTree(order)
        expected = set()
        for step in range(300):
            key = rng.randrange(80)
            if rng.random() < .55:
                tree.insert(key, key)
                expected.add(key)
            else:
                tree.delete(key)
                expected.discard(key)
            tree.validate()
            assert [k for k, _ in tree.traverse_leaves()] == sorted(expected)
            assert {k for k in range(80) if tree.find(k) is not None} == expected

@pytest.mark.parametrize('count', [5, 40])
def test_reopen_dimension_rejected_without_modification(tmp_path, count):
    path = tmp_path / 'db.sqlite'
    db = SecureVectorDB.open(path, embedding_dim=4)
    for i in range(count):
        db.insert(i, f'texto {i}')
    root = db.root_hash
    db.close()
    with pytest.raises(ValidationError):
        SecureVectorDB.open(path, embedding_dim=8)
    db = SecureVectorDB.open(path, embedding_dim=4)
    assert db.root_hash == root and db.verify_dataset()
    assert len(db.search_by_range(0, count)) == count
    db.close()

def test_rebuild_dimension_atomic():
    idx = KDTreeVectorIndex(4)
    idx.insert(1, [0.] * 4)
    with pytest.raises(ValueError):
        idx.rebuild([(2, [0.] * 8)])
    assert idx.knn([0.] * 4, 1) == [(1, 0.)]

@pytest.mark.parametrize('record_id', [True, 2**63, 2**70])
def test_invalid_id_preserves_database(tmp_path, record_id):
    db = SecureVectorDB.open(tmp_path / 'db.sqlite')
    db.insert(0, 'original')
    root = db.root_hash
    with pytest.raises(ValidationError):
        db.insert(record_id, 'invalido')
    assert db.root_hash == root and db.verify_dataset()
    assert len(db.store) == 1
    db.close()

@pytest.mark.parametrize('claim', ['exp', 'nbf'])
@pytest.mark.parametrize('value', ['abc', {}, [], True, float('nan'), float('inf')])
def test_bad_jwt_claim_denied(claim, value):
    token = create_hs256_jwt({claim: value}, 's')
    assert not JwtAuthProvider('s').authenticate({'Authorization': 'Bearer ' + token}).allowed

def test_bad_jwt_encoding_denied():
    header = _b64url_encode(json.dumps({'alg':'HS256'}).encode())
    tokens = [header + '.' + _b64url_encode(b'\xff\xfe') + '.x', create_hs256_jwt({'sub':'a'}, 's').rsplit('.', 1)[0] + '.é']
    for token in tokens:
        assert not JwtAuthProvider('s').authenticate({'Authorization': 'Bearer ' + token}).allowed

@pytest.mark.parametrize('record_id', [True, 2**63, 2**70])
def test_api_invalid_id_rejected(record_id):
    from pydantic import ValidationError as ModelError
    from secure_vector_db.api.server import InsertRequest
    with pytest.raises(ModelError):
        InsertRequest(record_id=record_id, text='invalido')

def test_concurrent_writes_and_reads_consistent():
    from concurrent.futures import ThreadPoolExecutor
    db = SecureVectorDB()
    def worker(base):
        for i in range(30):
            rid = base * 100 + i
            db.insert(rid, f'texto {rid}')
            assert db.search_by_id(rid).text == f'texto {rid}'
            db.semantic_search('texto', 3)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(worker, range(4)))
    assert len(db.store) == 120
    assert len(db.search_by_range(0, 400)) == 120
    assert db.verify_dataset()
