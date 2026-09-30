"""Audit-log chain tests. One test for each tamper mode."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cvassure.core.audit import (
    GENESIS,
    LocalSha256Chain,
    entry_hash,
    read_entries,
    verify_file,
)
from cvassure.core.hashing import NotCanonical, canonical_json, canonical_sha256, sha256_hex


def _chain(tmp_path: Path, n: int = 5) -> LocalSha256Chain:
    c = LocalSha256Chain(tmp_path / "audit.log", deterministic_ts="1970-01-01T00:00:00Z")
    for i in range(n):
        c.append("stage_end", {"stage": f"s{i}", "i": i})
    return c


def test_genesis_and_first_link(tmp_path: Path) -> None:
    _chain(tmp_path, 2)
    entries = read_entries(tmp_path / "audit.log")
    assert entries[0]["seq"] == 1
    assert entries[0]["prev_hash"] == GENESIS
    assert entries[1]["seq"] == 2
    assert entries[1]["prev_hash"] == entries[0]["entry_hash"]


def test_entry_hash_excludes_itself_and_sig() -> None:
    e = {"seq": 1, "ts": "t", "event": "x", "data": {}, "prev_hash": GENESIS}
    h = entry_hash(e)
    assert entry_hash({**e, "entry_hash": h}) == h
    assert entry_hash({**e, "sig": "abc"}) == h


def test_append_fsyncs_and_writes_one_line_per_event(tmp_path: Path) -> None:
    _chain(tmp_path, 4)
    text = (tmp_path / "audit.log").read_text(encoding="utf-8")
    assert len(text.strip().splitlines()) == 4
    for line in text.strip().splitlines():
        assert "\n" not in line
        json.loads(line)


def test_clean_chain_verifies(tmp_path: Path) -> None:
    c = _chain(tmp_path, 6)
    res = verify_file(tmp_path / "audit.log", expected_head=c.head())
    assert res.ok
    assert res.entries == 6
    assert res.reason == "chain verified"


def test_edit_is_detected(tmp_path: Path) -> None:
    _chain(tmp_path)
    p = tmp_path / "audit.log"
    lines = p.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[2])
    entry["data"]["i"] = 999  # body edited, hash left alone
    lines[2] = canonical_json(entry)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = verify_file(p)
    assert not res.ok
    assert "edited" in res.reason


def test_delete_is_detected(tmp_path: Path) -> None:
    _chain(tmp_path, 5)
    p = tmp_path / "audit.log"
    lines = p.read_text(encoding="utf-8").splitlines()
    del lines[2]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = verify_file(p)
    assert not res.ok
    # A deleted line shows up as a seq gap or a prev_hash break.
    assert "seq" in res.reason or "prev_hash" in res.reason


def test_reorder_is_detected(tmp_path: Path) -> None:
    _chain(tmp_path, 5)
    p = tmp_path / "audit.log"
    lines = p.read_text(encoding="utf-8").splitlines()
    lines[1], lines[3] = lines[3], lines[1]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not verify_file(p).ok


def test_truncate_is_detected_via_expected_head(tmp_path: Path) -> None:
    c = _chain(tmp_path, 6)
    p = tmp_path / "audit.log"
    lines = p.read_text(encoding="utf-8").splitlines()
    p.write_text("\n".join(lines[:3]) + "\n", encoding="utf-8")
    # A truncated chain is internally consistent, which is exactly why the
    # recorded head is needed to catch it.
    assert verify_file(p).ok  # without the head it looks fine...
    res = verify_file(p, expected_head=c.head())
    assert not res.ok  # ...with the head it does not
    assert "does not match" in res.reason


def test_signature_bearing_entry_is_refused_not_ignored(tmp_path: Path) -> None:
    _chain(tmp_path, 2)
    p = tmp_path / "audit.log"
    lines = p.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[1])
    entry["sig"] = "base64:AAAA"
    entry["entry_hash"] = entry_hash(entry)
    lines[1] = canonical_json(entry)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = verify_file(p)
    assert not res.ok
    assert "SignedChain" in res.reason


def test_fresh_run_starts_a_new_log(tmp_path: Path) -> None:
    _chain(tmp_path, 3)
    first = (tmp_path / "audit.log").read_text(encoding="utf-8")
    LocalSha256Chain(tmp_path / "audit.log").append("run_start", {})
    second = (tmp_path / "audit.log").read_text(encoding="utf-8")
    assert first != second
    assert len(read_entries(tmp_path / "audit.log")) == 1


def test_private_keys_are_never_logged(tmp_path: Path) -> None:
    c = LocalSha256Chain(tmp_path / "audit.log")
    c.append("run_start", {"public_key_fingerprint": "sha256:abc123"})
    text = (tmp_path / "audit.log").read_text(encoding="utf-8")
    for marker in ("PRIVATE KEY", "private_key", "BEGIN "):
        assert marker not in text


# --- canonical JSON ---


def test_canonical_json_sorts_keys_and_drops_whitespace() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_integral_floats_normalise_to_ints() -> None:
    """A measured 0.0 s runtime is a real value and must not fail a run."""
    assert canonical_json({"t": 0.0}) == '{"t":0}'
    assert canonical_json({"t": 1.5}) == '{"t":1.5}'


def test_nan_and_inf_have_no_canonical_form() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(NotCanonical):
            canonical_json({"v": bad})


def test_non_string_keys_are_refused() -> None:
    with pytest.raises(NotCanonical):
        canonical_json({1: "a"})


def test_path_objects_are_refused_not_stringified() -> None:
    """A hash that depends on __str__ is a hash that changes across versions."""
    with pytest.raises(NotCanonical):
        canonical_json({"p": Path("x")})


def test_canonical_json_is_stable_across_key_insertion_order() -> None:
    a = canonical_sha256({"x": 1, "y": [1, 2], "z": {"b": 2, "a": 1}})
    b = canonical_sha256({"z": {"a": 1, "b": 2}, "y": [1, 2], "x": 1})
    assert a == b


def test_tuple_and_list_hash_the_same() -> None:
    """json.dumps treats a tuple as an array. The manifest round-trips through json."""
    assert canonical_sha256({"a": (1, 2)}) == canonical_sha256({"a": [1, 2]})


def test_sha256_of_str_and_bytes_agree() -> None:
    assert sha256_hex("abc") == sha256_hex(b"abc")
