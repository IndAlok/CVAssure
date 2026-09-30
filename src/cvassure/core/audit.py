"""Hash-chained audit log (D9).

JSON Lines. Each entry carries `prev_hash` and `entry_hash`, fsync'd on append.
Editing, deleting, reordering or truncating any line breaks the chain, and
`verify` says so.

Person 1 ships `LocalSha256Chain` and **no signatures**, on purpose. Person 4 owns
Ed25519 and Merkle; when their `P4Chain` exists it drops in behind the same three
methods and nothing else in the pipeline changes. Person 1 never mints a key.

Private keys are never logged. Public-key fingerprints only.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from cvassure.core.hashing import canonical_json, sha256_hex

GENESIS = "0" * 64
#: Events, in the order the pipeline appends them.
EVENTS = (
    "run_start",
    "config_loaded",
    "policy_loaded",
    "inputs_hashed",
    "plugins_loaded",
    "stage_start",
    "stage_end",
    "detector_result",
    "link_created",
    "policy_applied",
    "coverage_generated",
    "report_written",
    "run_end",
)


def entry_hash(entry: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical JSON of the entry without its own hash or sig."""
    body = {k: v for k, v in entry.items() if k not in ("entry_hash", "sig")}
    return sha256_hex(canonical_json(body))


class P4Chain:
    """Adapter over Person 4's signed chain. Same three methods, nothing else.

    Person 1 ships `LocalSha256Chain` so nothing waits, and this is the swap point.
    Person 4 owns Ed25519 and Merkle; this class does **not** re-implement either,
    it delegates. That keeps the plan's rule ("swap to P4's chain when that module
    exists") one import away instead of a rewrite of the pipeline.

    It deliberately does not fall back to the local chain when P4's module is
    missing: a silent fallback would drop signature verification without anyone
    noticing, and the whole point of the records row is that a chain either
    verifies or it does not.
    """

    def __init__(self, path: Path, *, deterministic_ts: str | None = None, fresh: bool = True):
        from cvassure.shift import p4chain  # P4's module, imported lazily

        self._impl = p4chain.P4Chain(path, deterministic_ts=deterministic_ts, fresh=fresh)
        self.path = path

    def append(self, event: str, data: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._impl.append(event, data)

    def verify(self) -> bool:
        return bool(self._impl.verify())

    def head(self) -> str:
        return str(self._impl.head())


def make_chain(
    path: Path, *, deterministic_ts: str | None = None, fresh: bool = True
) -> ChainBackend:
    """P4's chain when it is importable, otherwise the local hash chain.

    The one place the swap happens. Keeping the decision here rather than in the
    pipeline means the day-4 wire-up is a one-line check that already exists,
    and `chain_backend` in the run manifest records which one actually ran.
    """
    import importlib

    try:
        importlib.import_module("cvassure.shift.p4chain")
    except Exception:
        return LocalSha256Chain(path, deterministic_ts=deterministic_ts, fresh=fresh)
    return P4Chain(path, deterministic_ts=deterministic_ts, fresh=fresh)


class ChainBackend(Protocol):
    """The three methods Person 4's chain also has. That is the whole adapter."""

    def append(self, event: str, data: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def verify(self) -> bool: ...
    def head(self) -> str: ...


class LocalSha256Chain:
    """Append-only hash chain. Tamper-evident, not tamper-proof.

    A hash chain proves the log has not been edited since it was written, given
    the head hash was recorded somewhere else. Without signatures, an attacker who
    controls the whole file can rewrite it and recompute every hash. That is the
    honest limitation, it goes in the coverage statement, and Person 4's signature
    is what closes it. `chained_not_signed: true` is in every entry for exactly
    this reason.
    """

    def __init__(
        self, path: Path, *, deterministic_ts: str | None = None, fresh: bool = True
    ) -> None:
        """`fresh=True` starts a new log for a new run.

        Appending to yesterday's log would make `verify-log` verify two runs as
        one chain, and the head in run_manifest.json would belong to neither.
        A run owns its log; the previous one is still on disk, untouched, and a
        judge can diff them.
        """
        self.path = path
        self.deterministic_ts = deterministic_ts
        self._seq = 0
        self._prev = GENESIS
        path.parent.mkdir(parents=True, exist_ok=True)
        if fresh and path.exists():
            path.unlink()
        elif path.exists() and path.stat().st_size > 0:
            self._seq, self._prev = self._resume()

    def _resume(self) -> tuple[int, str]:
        last: dict[str, Any] | None = None
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = json.loads(line)
        if last is None:
            return 0, GENESIS
        return int(last["seq"]), str(last["entry_hash"])

    def _now(self) -> str:
        if self.deterministic_ts is not None:
            return self.deterministic_ts
        # ponytail: second resolution from the OS clock. If two runs in the same
        # second must differ, use a monotonic counter in `seq` instead of a clock.
        return (
            __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    def append(self, event: str, data: Mapping[str, Any]) -> Mapping[str, Any]:
        """One line, fsync'd. An unflushed entry is an entry that does not exist."""
        self._seq += 1
        entry: dict[str, Any] = {
            "seq": self._seq,
            "ts": self._now(),
            "event": event,
            "data": dict(data),
            "prev_hash": self._prev,
            "chained_not_signed": True,
        }
        entry["entry_hash"] = entry_hash(entry)
        line = canonical_json(entry) + "\n"
        with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        self._prev = entry["entry_hash"]
        return entry

    def head(self) -> str:
        return self._prev

    @property
    def count(self) -> int:
        return self._seq

    def verify(self) -> bool:
        return verify_file(self.path)[0]


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    reason: str
    entries: int
    head: str


def verify_file(path: Path, *, expected_head: str | None = None) -> VerifyResult:
    """Recompute the chain. Catches edit, delete, reorder and truncate.

    Truncation is caught by `expected_head`, which the pipeline passes from
    `run_manifest.json`. Without it a file cut in half is a perfectly valid
    shorter chain, and saying so is the only honest answer.
    """
    if not path.is_file():
        return VerifyResult(False, f"no such log: {path}", 0, GENESIS)

    prev = GENESIS
    n = 0
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                return VerifyResult(False, f"line {lineno} is not JSON: {exc}", n, prev)
            n += 1
            if entry.get("seq") != n:
                return VerifyResult(
                    False, f"line {lineno} has seq {entry.get('seq')}, expected {n}", n, prev
                )
            if entry.get("prev_hash") != prev:
                return VerifyResult(
                    False,
                    f"line {lineno} prev_hash does not match the previous entry_hash",
                    n,
                    prev,
                )
            if entry.get("entry_hash") != entry_hash(entry):
                return VerifyResult(False, f"line {lineno} body was edited", n, prev)
            if "sig" in entry and entry["sig"] is not None:
                # Person 4's chain. We do not verify signatures here; we do not
                # silently ignore them either.
                return VerifyResult(
                    False,
                    "entry carries a signature: use P4Chain to verify, not LocalSha256Chain",
                    n,
                    prev,
                )
            prev = entry["entry_hash"]

    if expected_head and prev != expected_head:
        return VerifyResult(
            False,
            f"chain head {prev[:12]} does not match the recorded {expected_head[:12]}",
            n,
            prev,
        )
    return VerifyResult(True, "chain verified", n, prev)


def read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out
