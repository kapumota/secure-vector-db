"""Merkle incremental interno para integridad verificable."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Literal, Mapping

UpdateMode = Literal["path", "rebuild", "noop"]


@dataclass(frozen=True)
class MerkleNodeDigest:
    """Digest recalculado durante una actualizacion incremental."""

    level: int
    index: int
    digest_hex: str


@dataclass(frozen=True)
class MerkleUpdateResult:
    """Resultado de una operacion incremental sobre Merkle."""

    mode: UpdateMode
    root_hex: str
    touched_nodes: int


def _ensure_record_id(record_id: int) -> None:
    """Valida identificador de registro."""
    if not isinstance(record_id, int) or record_id < 0:
        raise ValueError("record_id debe ser un entero no negativo")


def _to_bytes(value: str | bytes) -> bytes:
    """Convierte valores soportados a bytes."""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


def hash_leaf(value: str | bytes) -> bytes:
    """Calcula hash de hoja con prefijo de dominio."""
    return hashlib.sha256(b"leaf:" + _to_bytes(value)).digest()


def hash_pair(left: bytes, right: bytes) -> bytes:
    """Calcula hash de nodo interno con prefijo de dominio."""
    return hashlib.sha256(b"node:" + left + right).digest()


def build_merkle_levels_from_digests(leaf_digests: list[bytes]) -> list[list[bytes]]:
    """Construye niveles Merkle desde hashes de hojas."""
    if not leaf_digests:
        return []

    levels = [list(leaf_digests)]
    current = list(leaf_digests)

    while len(current) > 1:
        if len(current) % 2:
            current = [*current, current[-1]]
        next_level = [
            hash_pair(current[index], current[index + 1])
            for index in range(0, len(current), 2)
        ]
        levels.append(next_level)
        current = next_level

    return levels


def compute_merkle_root_hex(items: Iterable[tuple[int, str | bytes]]) -> str:
    """Calcula raiz Merkle completa desde cero."""
    ordered = sorted(items, key=lambda item: item[0])
    if not ordered:
        return ""
    leaf_digests = [hash_leaf(value) for _, value in ordered]
    levels = build_merkle_levels_from_digests(leaf_digests)
    return levels[-1][0].hex()


class IncrementalMerkleTree:
    """Arbol Merkle incremental en memoria.

    Las actualizaciones sobre una llave existente recalculan solo la ruta a la raiz.
    Las inserciones y eliminaciones pueden cambiar la forma del arbol, por eso en
    esta fase reconstruyen la estructura interna completa de forma controlada.
    """

    def __init__(self, items: Iterable[tuple[int, str | bytes]] | None = None) -> None:
        self._leaf_hashes: dict[int, bytes] = {}
        self._keys: list[int] = []
        self._key_to_index: dict[int, int] = {}
        self._levels: list[list[bytes]] = []
        if items is not None:
            self.rebuild(items)

    @classmethod
    def from_items(cls, items: Iterable[tuple[int, str | bytes]]) -> "IncrementalMerkleTree":
        """Crea un arbol desde pares record_id y contenido canonico."""
        return cls(items)

    @classmethod
    def from_leaf_digests(
        cls,
        leaf_digests: Mapping[int, str | bytes],
    ) -> "IncrementalMerkleTree":
        """Crea un arbol desde digests de hojas ya calculados."""
        tree = cls()
        tree.rebuild_from_leaf_digests(leaf_digests)
        return tree

    def rebuild_from_leaf_digests(
        self,
        leaf_digests: Mapping[int, str | bytes],
    ) -> MerkleUpdateResult:
        """Reconstruye estructura interna desde digests de hojas."""
        parsed: dict[int, bytes] = {}
        for record_id, digest in leaf_digests.items():
            _ensure_record_id(record_id)
            if isinstance(digest, str):
                try:
                    digest_bytes = bytes.fromhex(digest)
                except ValueError as exc:
                    raise ValueError("digest de hoja invalido") from exc
            else:
                digest_bytes = digest

            if len(digest_bytes) != 32:
                raise ValueError("digest de hoja debe tener 32 bytes")
            parsed[record_id] = digest_bytes

        self._leaf_hashes = parsed
        self._rebuild_levels_from_leaf_hashes()
        return MerkleUpdateResult(
            mode="rebuild",
            root_hex=self.root_hex,
            touched_nodes=self._count_nodes(),
        )

    @property
    def size(self) -> int:
        """Cantidad de hojas activas."""
        return len(self._leaf_hashes)

    @property
    def root_hex(self) -> str:
        """Raiz Merkle actual en hexadecimal."""
        if not self._levels:
            return ""
        return self._levels[-1][0].hex()

    def contains(self, record_id: int) -> bool:
        """Indica si una hoja existe."""
        _ensure_record_id(record_id)
        return record_id in self._leaf_hashes

    def leaf_digest_hex(self, record_id: int) -> str:
        """Devuelve digest de hoja en hexadecimal."""
        _ensure_record_id(record_id)
        if record_id not in self._leaf_hashes:
            raise KeyError("record_id no existe en Merkle incremental")
        return self._leaf_hashes[record_id].hex()

    def rebuild(self, items: Iterable[tuple[int, str | bytes]]) -> MerkleUpdateResult:
        """Reconstruye estructura interna desde cero."""
        leaf_hashes: dict[int, bytes] = {}
        for record_id, value in items:
            _ensure_record_id(record_id)
            leaf_hashes[record_id] = hash_leaf(value)

        self._leaf_hashes = leaf_hashes
        self._rebuild_levels_from_leaf_hashes()
        return MerkleUpdateResult(
            mode="rebuild",
            root_hex=self.root_hex,
            touched_nodes=self._count_nodes(),
        )

    def update_leaf(self, record_id: int, value: str | bytes) -> MerkleUpdateResult:
        """Actualiza una hoja existente o inserta una nueva."""
        _ensure_record_id(record_id)
        new_digest = hash_leaf(value)

        if record_id not in self._leaf_hashes:
            self._leaf_hashes[record_id] = new_digest
            self._rebuild_levels_from_leaf_hashes()
            return MerkleUpdateResult(
                mode="rebuild",
                root_hex=self.root_hex,
                touched_nodes=self._count_nodes(),
            )

        if self._leaf_hashes[record_id] == new_digest:
            return MerkleUpdateResult(mode="noop", root_hex=self.root_hex, touched_nodes=0)

        self._leaf_hashes[record_id] = new_digest
        path = self.recompute_path_to_root(record_id)
        return MerkleUpdateResult(
            mode="path",
            root_hex=self.root_hex,
            touched_nodes=len(path),
        )

    def delete_leaf(self, record_id: int) -> MerkleUpdateResult:
        """Elimina una hoja y reconstruye la forma interna."""
        _ensure_record_id(record_id)
        if record_id not in self._leaf_hashes:
            return MerkleUpdateResult(mode="noop", root_hex=self.root_hex, touched_nodes=0)

        del self._leaf_hashes[record_id]
        self._rebuild_levels_from_leaf_hashes()
        return MerkleUpdateResult(
            mode="rebuild",
            root_hex=self.root_hex,
            touched_nodes=self._count_nodes(),
        )

    def recompute_path_to_root(self, record_id: int) -> list[MerkleNodeDigest]:
        """Recalcula la ruta de una hoja existente hasta la raiz."""
        _ensure_record_id(record_id)
        if record_id not in self._key_to_index:
            raise KeyError("record_id no existe en Merkle incremental")
        if not self._levels:
            return []

        index = self._key_to_index[record_id]
        self._levels[0][index] = self._leaf_hashes[record_id]
        touched = [MerkleNodeDigest(level=0, index=index, digest_hex=self._levels[0][index].hex())]

        current_index = index
        for level in range(1, len(self._levels)):
            parent_index = current_index // 2
            left_index = parent_index * 2
            right_index = left_index + 1
            previous_level = self._levels[level - 1]
            left = previous_level[left_index]
            right = previous_level[right_index] if right_index < len(previous_level) else left
            digest = hash_pair(left, right)
            self._levels[level][parent_index] = digest
            touched.append(MerkleNodeDigest(level=level, index=parent_index, digest_hex=digest.hex()))
            current_index = parent_index

        return touched

    def verify_against_full_rebuild(self) -> bool:
        """Compara raiz incremental contra reconstruccion completa."""
        full_root = self.compute_full_root_hex()
        return self.root_hex == full_root

    def compute_full_root_hex(self) -> str:
        """Calcula raiz desde cero usando las hojas actuales."""
        ordered = ((record_id, self._leaf_hashes[record_id]) for record_id in self._keys)
        if not self._keys:
            return ""
        leaf_digests = [digest for _, digest in ordered]
        levels = build_merkle_levels_from_digests(leaf_digests)
        return levels[-1][0].hex()

    def snapshot_leaf_digests(self) -> dict[int, str]:
        """Devuelve snapshot seguro de hojas para diagnostico."""
        return {record_id: digest.hex() for record_id, digest in sorted(self._leaf_hashes.items())}

    def _rebuild_levels_from_leaf_hashes(self) -> None:
        """Reconstruye niveles internos desde hashes de hojas."""
        self._keys = sorted(self._leaf_hashes)
        self._key_to_index = {record_id: index for index, record_id in enumerate(self._keys)}
        leaf_digests = [self._leaf_hashes[record_id] for record_id in self._keys]
        self._levels = build_merkle_levels_from_digests(leaf_digests)

    def _count_nodes(self) -> int:
        """Cuenta nodos materiales en memoria."""
        return sum(len(level) for level in self._levels)
