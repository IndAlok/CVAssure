"""Canonical JSON and hashing. One implementation, shared by everything.

The audit log, the record chain, the config hash and the report payload hash all
need "the same bytes from the same object". Four different canonicalisers is four
opportunities for a hash to disagree, so there is one.

**This is not full RFC 8785.** It is the minimal canonicaliser from the plan:
UTF-8, object keys sorted, no insignificant whitespace, integers without a fraction.
See `docs/research/standards.md`. Do not claim RFC 8785 compliance.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

CHUNK = 1024 * 1024


class NotCanonical(ValueError):
    """An object that cannot be canonicalised. Fails closed, never guesses."""


def _normalise(obj: Any, path: str = "$") -> Any:
    """Return a copy with integral floats written as ints. Rejects NaN and Inf.

    The rule from the plan is "numbers that are integers written without a
    fraction". That is a *normalisation*, not a rejection: a measured runtime of
    0.0 seconds is a real value and must not fail a run. What must fail is a
    value with no canonical form at all.
    """
    if isinstance(obj, bool) or obj is None or isinstance(obj, (str, int)):
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise NotCanonical(f"{path}: {obj!r} is NaN or Inf and has no canonical form")
        return int(obj) if obj == int(obj) and abs(obj) < 2**53 else obj
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise NotCanonical(f"{path}: object key {k!r} is not a string")
            out[k] = _normalise(v, f"{path}.{k}")
        return out
    if isinstance(obj, (list, tuple)):
        return [_normalise(v, f"{path}[{i}]") for i, v in enumerate(obj)]
    # Path, datetime, Decimal and friends: not canonicalisable, and silently
    # stringifying them would let a hash depend on __str__ output.
    raise NotCanonical(f"{path}: {type(obj).__name__} is not a canonical JSON type")


def canonical_json(obj: Any) -> str:
    """Deterministic text for one object. Same input, same bytes, every machine."""
    return json.dumps(
        _normalise(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(obj: Any) -> str:
    return sha256_hex(canonical_json(obj))


def file_sha256(path: Path) -> str:
    """Streamed, so a 2 GB model file does not land in memory."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def tree_sha256(root: Path, patterns: tuple[str, ...] = ("*",)) -> str:
    """Digest of a directory's contents: sorted relative paths plus file digests.

    Used for the dataset input hash. Order-independent and path-relative, so the
    same dataset hashes the same on Linux and Windows despite separator
    differences.
    """
    seen: list[tuple[str, str]] = []
    for pattern in patterns:
        for p in sorted(root.rglob(pattern)):
            if p.is_file():
                seen.append((p.relative_to(root).as_posix(), file_sha256(p)))
    return canonical_sha256(sorted(seen))
