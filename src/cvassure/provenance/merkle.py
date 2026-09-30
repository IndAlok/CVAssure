"""Merkle tree for batch roots.

Append-only, in-memory binary Merkle tree. Leaves are entry_hash values
from the audit log or signed records. The root commits to all leaves.

Used as a stretch feature: SignedChain optionally adds leaves and records
the merkle_root in the run_end entry.

The hashing follows RFC 6962 (Certificate Transparency) leaf/node domain
separation:
  leaf hash  = SHA-256(0x00 || leaf_data)
  node hash  = SHA-256(0x01 || left || right)

This prevents second-preimage attacks where an internal node can be
confused with a leaf.
"""

from __future__ import annotations

import hashlib
from typing import NamedTuple


def _leaf_hash(data: bytes | str) -> str:
    """SHA-256 with RFC 6962 domain separation for leaves."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(b"\x00" + data).hexdigest()


def _node_hash(left: str, right: str) -> str:
    """SHA-256 with RFC 6962 domain separation for internal nodes."""
    return hashlib.sha256(b"\x01" + bytes.fromhex(left) + bytes.fromhex(right)).hexdigest()


def _build_tree(leaves: list[str]) -> list[list[str]]:
    """Build levels bottom-up. levels[0] is the leaves, levels[-1] is the root."""
    if not leaves:
        return [[]]
    levels: list[list[str]] = [list(leaves)]
    current = list(leaves)
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else left  # duplicate last if odd
            next_level.append(_node_hash(left, right))
        levels.append(next_level)
        current = next_level
    return levels


EMPTY_ROOT = hashlib.sha256(b"").hexdigest()


class ProofStep(NamedTuple):
    """One step in an audit proof."""

    sibling: str  # hex hash of the sibling node
    side: str  # "left" or "right" — which side the sibling is on


class MerkleTree:
    """Append-only Merkle tree.

    Leaves are added one at a time. The tree is rebuilt on each addition.
    For the small logs CVAssure produces (tens to hundreds of entries),
    the O(n) rebuild is acceptable.
    """

    def __init__(self) -> None:
        self._leaves: list[str] = []  # hex hashes

    def add_leaf(self, entry_hash: str) -> None:
        """Add one leaf (the entry_hash of a log entry)."""
        self._leaves.append(_leaf_hash(entry_hash))

    def root(self) -> str:
        """Current Merkle root. Returns EMPTY_ROOT for an empty tree."""
        if not self._leaves:
            return EMPTY_ROOT
        levels = _build_tree(self._leaves)
        return levels[-1][0]

    def __len__(self) -> int:
        return len(self._leaves)

    def proof(self, index: int) -> list[ProofStep]:
        """Compute the audit proof for leaf at position ``index``.

        Returns a list of ProofStep. Verify with ``verify_proof``.
        """
        if not self._leaves:
            raise IndexError("empty tree")
        if index < 0 or index >= len(self._leaves):
            raise IndexError(f"index {index} out of range [0, {len(self._leaves)})")
        levels = _build_tree(self._leaves)
        steps: list[ProofStep] = []
        pos = index
        for level in levels[:-1]:  # don't include the root level
            if pos % 2 == 0:
                # We are a left child; sibling is to the right
                sibling_pos = pos + 1
                if sibling_pos < len(level):
                    steps.append(ProofStep(sibling=level[sibling_pos], side="right"))
                else:
                    steps.append(ProofStep(sibling=level[pos], side="right"))  # odd — duplicate
            else:
                # We are a right child; sibling is to the left
                steps.append(ProofStep(sibling=level[pos - 1], side="left"))
            pos //= 2
        return steps

    @staticmethod
    def verify_proof(leaf_entry_hash: str, proof: list[ProofStep], expected_root: str) -> bool:
        """Verify an audit proof. Returns True if the leaf is in the tree with the given root."""
        current = _leaf_hash(leaf_entry_hash)
        for step in proof:
            if step.side == "right":
                current = _node_hash(current, step.sibling)
            else:
                current = _node_hash(step.sibling, current)
        return current == expected_root

    def to_dict(self) -> dict:
        """Serialisable representation for embedding in the run manifest."""
        return {
            "leaf_count": len(self._leaves),
            "root": self.root(),
            "algorithm": "sha256-rfc6962",
        }
