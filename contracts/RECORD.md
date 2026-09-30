# RECORD — signed inference records

**Owner:** Person 4. **Status:** STRAWMAN, day 1. Person 1 wrote it, **Person 4 owns every
field and the crypto.** I do not re-implement Ed25519 or Merkle; I consume them.

---

## 1. What a record is

One inference output, bound to everything that produced it: the input image, the model
identifier or weight digest, the preprocessing and inference configuration, and the output.
PS §2.2.3.

That binding is the whole point. An attacker who can edit a record after the fact must break a
signature to hide it.

```json
{
  "input_hash": "sha256:3f2a…",
  "model_digest": "sha256:9c11…",
  "config_hash": "sha256:4de0…",
  "output": { "label": 3, "score": 0.91, "bbox": [0.1, 0.2, 0.3, 0.4] },
  "nonce": "9f2c8a1b",
  "sequence": 41,
  "timestamp": "2026-09-30T09:14:22Z",
  "prev_hash": "sha256:77ab…",
  "signature": "base64:MEUCIQD…"
}
```

| field | rule | tamper it makes visible |
|---|---|---|
| `input_hash` | sha256 of the input bytes, hex or `sha256:` prefixed — pick one and say so here | the input was swapped |
| `model_digest` | the wrapper's `weight_digest()` at inference time | a different model answered |
| `config_hash` | canonical hash of preprocessing + inference config | preprocessing was changed |
| `output` | the raw model output, not a post-processed label | the answer was edited |
| `nonce` | unique per record, random | replay |
| `sequence` | monotonically increasing, gapless within a file | deletion, reordering |
| `timestamp` | RFC 3339 UTC | backdating |
| `prev_hash` | hash of the previous record | reordering, splicing a foreign file in |
| `signature` | Ed25519 over the canonical JSON of everything above, base64 | any edit at all |

**Signature covers `prev_hash`.** Without it, `prev_hash` is decorative and an attacker can
rebuild a consistent-looking file.

---

## 2. Canonical JSON

The record is signed over canonical bytes, so both sides must produce the same bytes from the
same object. Reuse **the same canonicaliser Person 1 uses for the audit log** — it lives in
`cvassure.core.hashing` and I will export it in Phase 3. Do not write a second one.

- UTF-8
- object keys sorted
- no insignificant whitespace
- integers written without a fraction

That is the minimal canonicaliser, **not full RFC 8785**. If you need full JCS, raise it in
standup and I will pin the `rfc8785` package instead. Do not claim RFC 8785 compliance for a
canonicaliser that does not implement it.

---

## 3. File layout

```text
records/
  records.jsonl          # one record per line, ordered by sequence
  public_key.pem         # or .bin, raw 32 bytes — Person 4 ships it
  MANIFEST.json          # optional: chain head, record count, public key fingerprint
```

JSON Lines, one record per line, no pretty printing. A tampered or truncated tail must be
detectable, so the line count and the final `prev_hash` are both recorded in `MANIFEST.json`
and echoed in my `run_manifest.json`.

**Public key path** is passed to me as `--pubkey` and lands in `AuditContext.pubkey_path`. I
log the **fingerprint only**. Never a private key, never a key file, in any log, fixture or
screenshot.

---

## 4. The three functions I call

This is the adapter surface. `ChainBackend` in `cvassure.core.audit` has exactly these three.

```python
class ChainBackend(Protocol):
    def append(self, event: str, data: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def verify(self) -> bool: ...
    def head(self) -> str: ...
```

From your side, whatever shape you prefer internally:

```python
append(event: str, data: dict) -> dict   # append one record, return it
verify(path: Path, pubkey: Path) -> bool # full chain + signature check
head(path: Path) -> str                  # hex of the final entry hash
```

**Day 2–3 you are not needed.** I ship `LocalSha256Chain`: a hash chain with no signatures, so
the audit log is tamper-evident on day 2. Day 4 you drop in `P4Chain`, same three methods, and
the rest of the pipeline does not change. If you are late, nothing blocks.

**What I need from you for `verify()` to be meaningful:** it must return `False`, not raise,
on a bad signature, a broken `prev_hash`, a sequence gap, and a reused nonce. I wrap the
exception either way, but a boolean is easier to test and easier to log.

---

## 5. What the pipeline expects the verifier to find

The demo scenario has exactly two failures, and the report must show both with different
reasons:

| record | modification | detection | tag |
|---|---|---|---|
| `rec-0007` | `output` edited after signing | signature no longer verifies over the canonical bytes | `verification_failed` |
| `rec-0012` | replayed, nonce `9f2c…` already consumed at sequence 41 | nonce reuse, and `sequence` is behind the chain head | `replay` + `verification_failed` |

Both become `asset: records`, `disposition: rejected`. `rejected` exists because failed
records are not a judgement call — a record that fails verification did not happen as claimed.

**The compromised-key case is a limitation, not a finding.** If the signing key is
compromised, every signature verifies and nothing is detectable. That goes in the records row
of the coverage statement as a limitation line, and I need a way for the verifier to *say*
that (`MANIFEST.json` flag) so the run can be honest. It must never print a clean result when
the key is known-compromised.

---

## 6. Your detector, my interface

You register under the id `records.verify`:

```toml
[project.entry-points."cvassure.detectors"]
records_verify = "cvassure.provenance.verify:RecordVerifier"
```

`asset = "records"`, `owner = "P4"`, `requires = frozenset()`. Emit **one Finding per failed
record**, not one summary Finding — the plan's §20 narrative wants 2 rejected records, and a
single rolled-up finding cannot express "one edited, one replayed". Set `sample_ids=[record_id]`,
`metadata.record_seq`, and put the failure kind in `metadata.modification`.

`summary` on the CLI line should carry the breakdown, e.g. `120 records  2 REJECTED (1 edited,
1 replayed)`.

---

## 7. Acknowledgement

Tagging `contracts-v1` confirms the field names and the three-function surface.

- [ ] **P4** — field names, canonical-JSON reuse, file layout. **PENDING day 1**
- [ ] **P1** — three-method adapter surface, `LocalSha256Chain` until you land. Acknowledged
- [ ] **P5** — will generate `rec-0007` tampered and `rec-0012` replayed. **PENDING**
