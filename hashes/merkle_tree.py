"""Simple Merkle-like hash tree utilities. (Utilidades simples de árbol hash tipo Merkle.)"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class MerkleTree:
    """In-memory Merkle tree container. (Contenedor en memoria de árbol Merkle.)"""

    leaves: List[str]
    levels: List[List[str]]
    root: str


def _hash_bytes(payload: bytes) -> str:
    """Hash raw bytes with SHA-256. (Hashea bytes crudos con SHA-256.)"""
    return hashlib.sha256(payload).hexdigest()


def _chunk_bytes(data: bytes, chunk_size: int) -> Iterable[bytes]:
    """Yield fixed-size chunks from data. (Genera chunks de tamaño fijo del dato.)"""
    if chunk_size <= 0:
        raise ValueError("chunk_size_must_be_positive")
    for offset in range(0, len(data), chunk_size):
        yield data[offset : offset + chunk_size]


def _build_level(nodes: List[str]) -> List[str]:
    """Build the next level of hashes. (Construye el siguiente nivel de hashes.)"""
    if not nodes:
        raise ValueError("nodes_empty")
    if len(nodes) == 1:
        return nodes
    parents: List[str] = []
    for index in range(0, len(nodes), 2):
        left = nodes[index]
        right = nodes[index + 1] if index + 1 < len(nodes) else left
        parent_payload = f"{left}{right}".encode("utf-8")
        parents.append(_hash_bytes(parent_payload))
    return parents


def build_merkle_tree(data: bytes, chunk_size: int = 1024) -> MerkleTree:
    """Build a Merkle-like tree from data. (Construye un árbol tipo Merkle desde datos.)"""
    leaves = [_hash_bytes(chunk) for chunk in _chunk_bytes(data, chunk_size)]
    if not leaves:
        leaves = [_hash_bytes(b"")]
    levels: List[List[str]] = [leaves]
    current = leaves
    while len(current) > 1:
        current = _build_level(current)
        levels.append(current)
    return MerkleTree(leaves=leaves, levels=levels, root=levels[-1][0])


def verify_merkle_root(data: bytes, expected_root: str, chunk_size: int = 1024) -> bool:
    """Verify that data matches an expected root. (Verifica que los datos coinciden con la raíz esperada.)"""
    tree = build_merkle_tree(data, chunk_size=chunk_size)
    return tree.root == expected_root
