"""Persistencia y recovery de Merkle incremental."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from secure_vector_db.crypto.incremental_merkle import (
    IncrementalMerkleTree,
    build_merkle_levels_from_digests,
)


class MerkleRecoveryError(RuntimeError):
    """Error de recovery de Merkle incremental."""


@dataclass(frozen=True)
class MerklePersistenceStats:
    """Estadisticas de persistencia Merkle."""

    leaves: int
    nodes: int
    root_hex: str
    recovered_from: str


def _decode_digest_hex(digest_hex: str) -> bytes:
    """Convierte digest hexadecimal a bytes."""
    try:
        digest = bytes.fromhex(digest_hex)
    except ValueError as exc:
        raise MerkleRecoveryError("digest Merkle invalido") from exc
    if len(digest) != 32:
        raise MerkleRecoveryError("digest Merkle debe tener 32 bytes")
    return digest


def _nodes_from_leaf_digests(leaf_digests: dict[int, str]) -> list[tuple[int, int, str]]:
    """Construye nodos persistibles desde digests de hojas."""
    ordered = sorted(leaf_digests.items())
    if not ordered:
        return []

    leaf_bytes = [_decode_digest_hex(digest_hex) for _, digest_hex in ordered]
    levels = build_merkle_levels_from_digests(leaf_bytes)
    rows: list[tuple[int, int, str]] = []

    for level, digests in enumerate(levels):
        for index, digest in enumerate(digests):
            rows.append((level, index, digest.hex()))

    return rows


class SQLiteMerkleNodeStore:
    """Almacen SQLite para hojas y nodos Merkle."""

    schema_version = 1

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        """Inicializa tablas de persistencia Merkle."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS merkle_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS merkle_leaves (
                    record_id INTEGER PRIMARY KEY,
                    digest_hex TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS merkle_nodes (
                    level INTEGER NOT NULL,
                    node_index INTEGER NOT NULL,
                    digest_hex TEXT NOT NULL,
                    PRIMARY KEY (level, node_index)
                )
                """
            )
            connection.commit()

    def save_tree(self, tree: IncrementalMerkleTree) -> MerklePersistenceStats:
        """Persiste hojas, nodos y raiz actual."""
        self.initialize()
        leaf_digests = tree.snapshot_leaf_digests()
        node_rows = _nodes_from_leaf_digests(leaf_digests)

        with self._connect() as connection:
            connection.execute("DELETE FROM merkle_metadata")
            connection.execute("DELETE FROM merkle_leaves")
            connection.execute("DELETE FROM merkle_nodes")

            connection.executemany(
                "INSERT INTO merkle_leaves(record_id, digest_hex) VALUES (?, ?)",
                sorted(leaf_digests.items()),
            )
            connection.executemany(
                "INSERT INTO merkle_nodes(level, node_index, digest_hex) VALUES (?, ?, ?)",
                node_rows,
            )
            connection.executemany(
                "INSERT INTO merkle_metadata(key, value) VALUES (?, ?)",
                [
                    ("schema_version", str(self.schema_version)),
                    ("root_hex", tree.root_hex),
                    ("leaf_count", str(tree.size)),
                ],
            )
            connection.commit()

        return MerklePersistenceStats(
            leaves=tree.size,
            nodes=len(node_rows),
            root_hex=tree.root_hex,
            recovered_from="save",
        )

    def load_leaf_digests(self) -> dict[int, str]:
        """Carga hojas persistidas."""
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record_id, digest_hex FROM merkle_leaves ORDER BY record_id"
            ).fetchall()
        return {int(record_id): str(digest_hex) for record_id, digest_hex in rows}

    def load_root_hex(self) -> str:
        """Carga raiz persistida."""
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM merkle_metadata WHERE key = ?",
                ("root_hex",),
            ).fetchone()
        return "" if row is None else str(row[0])

    def count_nodes(self) -> int:
        """Cuenta nodos persistidos."""
        self.initialize()
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) FROM merkle_nodes").fetchone()
        return int(row[0]) if row is not None else 0

    def recover_tree(self) -> tuple[IncrementalMerkleTree, MerklePersistenceStats]:
        """Recupera arbol Merkle desde hojas persistidas."""
        leaf_digests = self.load_leaf_digests()
        tree = IncrementalMerkleTree.from_leaf_digests(leaf_digests)
        persisted_root = self.load_root_hex()

        if persisted_root and persisted_root != tree.root_hex:
            raise MerkleRecoveryError("raiz Merkle persistida no coincide con hojas")

        nodes = self.count_nodes()
        recovered_from = "leaves" if nodes == 0 and leaf_digests else "nodes"

        return (
            tree,
            MerklePersistenceStats(
                leaves=tree.size,
                nodes=nodes,
                root_hex=tree.root_hex,
                recovered_from=recovered_from,
            ),
        )

    def verify_integrity(self) -> bool:
        """Verifica raiz persistida contra hojas persistidas."""
        try:
            tree, _ = self.recover_tree()
        except MerkleRecoveryError:
            return False
        persisted_root = self.load_root_hex()
        return persisted_root == tree.root_hex

    def rebuild_missing_nodes(self) -> MerklePersistenceStats:
        """Reconstruye nodos internos desde hojas persistidas."""
        tree, _ = self.recover_tree()
        return self.save_tree(tree)

    def replace_leaf_digest_for_test(self, record_id: int, digest_hex: str) -> None:
        """Permite simular corrupcion en pruebas controladas."""
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                "UPDATE merkle_leaves SET digest_hex = ? WHERE record_id = ?",
                (digest_hex, record_id),
            )
            connection.commit()

    def delete_nodes_for_test(self) -> None:
        """Permite simular perdida de nodos internos en pruebas controladas."""
        self.initialize()
        with self._connect() as connection:
            connection.execute("DELETE FROM merkle_nodes")
            connection.commit()

    def iter_node_rows_for_test(self) -> Iterable[tuple[int, int, str]]:
        """Devuelve nodos persistidos para pruebas."""
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT level, node_index, digest_hex FROM merkle_nodes ORDER BY level, node_index"
            ).fetchall()
        return [(int(level), int(index), str(digest)) for level, index, digest in rows]

    def _connect(self) -> sqlite3.Connection:
        """Abre conexion SQLite local."""
        return sqlite3.connect(self.database_path)
