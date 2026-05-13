from __future__ import annotations
from secure_vector_db.database import SecureVectorDB

class Node:
    """Nodo distribuido mínimo: cada nodo mantiene una DB y publica su Merkle root."""
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.db = SecureVectorDB()

    def status(self) -> dict:
        return {'node_id': self.node_id, 'records': len(self.db.store), 'root_hash': self.db.root_hash}
