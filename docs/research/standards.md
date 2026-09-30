# Standards this repo follows, and what each one changed here

**Owner:** Person 1. Written day 6 (D16, `docs/research/standards.md`).

Each section is a short factual note, then **at most five lines on what it changes in this repo**.
The rule from the plan: do not claim compliance we did not implement.

---

## 1. JSON Schema 2020-12

**What it is.** The current JSON Schema dialect, published by the JSON Schema organisation. It is
the successor to Draft 7 and it changes keyword semantics in ways that matter for a validator
claim: `$defs` replaces `definitions`, `prefixItems` replaces the array form of `items`, and
dynamic references exist.

**Why 2020-12 and not Draft 7.** Draft 7 is the dialect most tooling *defaults* to, which is
exactly why it is worth naming a dialect explicitly rather than inheriting whatever a library's
default happens to be. Both were available to us; Draft 7 was rejected because there is no reason
to ship a contract against a superseded dialect when the validator we depend on implements the
current one.

**What it changed here.**

- `contracts/finding.schema.json` and `finding.draft.schema.json` declare
  `"$schema": "https://json-schema.org/draft/2020-12/schema"`.
- Validation is Python `jsonschema`'s `Draft202012Validator`, asserted in
  `tests/core/test_finding.py::test_schemas_are_valid_draft_2020_12`.
- `additionalProperties: false` at the top level is the schema-level half of the honesty rule: an
  unknown key is a bug, not an extension point.
- The schemas are **generated** from the Pydantic model and committed; a test asserts the
  committed file still equals the generated document, so the two cannot drift.
- We do not use dynamic references or the vocabulary system. One dialect is named and used.

Sources: <https://json-schema.org/draft/2020-12/schema> ·
<https://python-jsonschema.readthedocs.io/en/stable/>

---

## 2. RFC 8785 — JSON Canonicalization Scheme: **not implemented**

**What it is.** A specification for serialising JSON deterministically, so that two parties compute
the same bytes — and therefore the same hash — for the same object.

**What we actually shipped.** The minimal canonicaliser in `src/cvassure/core/hashing.py`:
UTF-8, object keys sorted, no insignificant whitespace, integers written without a fraction,
non-finite numbers rejected. It is **not full RFC 8785** and the module docstring says so.

**Where our version differs, concretely.** RFC 8785 prescribes IEEE-754 double rounding and
ES6 `Number::toString` formatting for numbers. We do not implement that. Our equivalence rule is
the plan's rule ("numbers that are integers written without a fraction"), which is a
normalisation, not the spec's algorithm. Any value that cannot be canonicalised — NaN, Inf, a
`Path`, a `datetime` — raises `NotCanonical` rather than being silently stringified, because a
hash that depends on `__str__` output is a hash nobody can reproduce.

**What it changed here.**

- `docs/research/standards.md` (this file) carries the words "**not full RFC 8785**", as the plan
  requires when the package cannot be confirmed.
- The audit log, record chain, config hash and report payload hash all route through the one
  canonicaliser, so the three cannot disagree.
- If full RFC 8785 is ever required, it is a change in one module and a re-hash of every stored
  digest — an explicit, versioned event, not a quiet swap.
- The `rfc8785` PyPI package was not evaluated on the day this was written; no claim depends on it.

Sources: <https://www.rfc-editor.org/rfc/rfc8785.html> (the specification as published) —
**note:** we read the plan's description of it, and our implementation follows the plan's minimal
rule, so no line of this repo should be read as a claim of RFC 8785 compliance.

---

## 3. RFC 8032 — Ed25519: consumed, never reimplemented

**What it is.** EdDSA signatures over Curve25519 — the signature scheme Person 4 uses for
inference records and, later, for audit-log entries.

**What it changed here.**

- Person 1 ships `LocalSha256Chain`: a hash chain with **no signatures**, so nothing waits.
- When Person 4's chain is importable at `cvassure.shift.p4chain:P4Chain`,
  `cvassure.core.audit.make_chain` picks it up automatically and the run manifest records
  `chain_backend`. Person 1 does not implement the adapter in advance and does not guess its
  interface.
- **Person 1 does not mint signing keys and does not implement Ed25519.** No `cryptography` import
  lives in `cvassure.core`.
- The audit log stores public-key fingerprints only. Never a private key, in the log or in a test.
- `LocalSha256Chain` is tamper-evident, not tamper-proof: an attacker who can rewrite the file can
  recompute every hash. That is why the head is also written to `run_manifest.json`, and why
  signatures are what upgrade it. The distinction is stated in the CLI output rather than papered
  over.

Sources: <https://www.rfc-editor.org/rfc/rfc8032.html> · <https://github.com/ossf/model-signing-spec>
(OpenSSF Model Signing, the naming reference for Person 4's artefact signing)

---

## 4. RFC 6962 — Merkle trees: displayed, not implemented

**What it is.** The Certificate Transparency Merkle tree specification: append-only logs with
inclusion and consistency proofs.

**What it changed here.**

- Person 1 does not implement Merkle inclusion proofs. Person 4 owns that as a stretch.
- If Person 4's verifier output carries a Merkle root, the report displays it; if it does not,
  nothing is displayed and nothing is claimed.
- The audit log's event order is the append-only part; our chain proves order and content much
  more weakly than a Merkle log with consistency proofs.
- No wording anywhere in this repo claims Certificate Transparency equivalence.

Source: <https://www.rfc-editor.org/rfc/rfc6962.html>

---

## 5. Model cards (Mitchell et al. 2019) and datasheets (Gebru et al.): field names for stretch S2

**What they are.** Documentation formats. Model cards describe a model's intended use, factors,
metrics and ethical considerations; datasheets describe a dataset's motivation, composition,
collection and recommended uses.

**What it changed here.**

- Nothing in the MVP. These field names are reserved for **stretch S2** (`src/cvassure/core/cards.py`),
  which is not implemented and must not be described as working.
- S2's planned cards are deliberately *shorter* than the research formats: manifest hash, model
  digest, finding summary, coverage status, canonicalised and signed with Person 4's key, plus
  `cvassure card verify`.
- A missing card would be a Finding, not a crash — a card is a claim, and a missing claim is worth
  reporting.
- Field names, when S2 lands, come from these formats so a reader recognises them.

Sources: Mitchell et al., 2019, *Model Cards for Model Reporting* —
<https://arxiv.org/abs/1810.03993>; Gebru et al., 2021, *Datasheets for Datasets* —
<https://arxiv.org/abs/1803.09010>. Both re-opened 30 September 2026.

---

## 6. Why a YAML `when`/`then` DSL instead of OPA / Rego

**What OPA is.** Open Policy Agent, a general-purpose policy engine that evaluates Rego, a
declarative language with a Datalog-derived core. It is the standard answer to "the policy logic is
getting complicated".

**What it changed here.**

- `policies/default.yaml` is a declarative `when`/`then` document with a fixed operator set
  (`eq`, `ne`, `gte`, `lte`, `gt`, `lt`, `in`, `contains`), loaded with `yaml.safe_load` only.
  **No `eval`, no `exec`, no `simpleeval`.** A `!!python/object` YAML tag fails closed, and there
  is a test per failure mode.
- An unknown field or operator is a config error (**exit 2**), not a skip. A policy that silently
  ignores a rule a judge can see in the file is worse than one that refuses to run.
- The DSL cannot express loops or arithmetic beyond the linker's own formula, and
  `docs/p1/POLICY.md` says so in one line rather than implying completeness.
- OPA would add a second binary or a subprocess to an air-gapped CPU tool, plus a language whose
  behaviour a judge cannot read off the file. For four rules over flat Finding fields, the
  evaluator is a `for` loop over 8 operators.
- The cost is real and accepted: if policy ever needs aggregation, arithmetic or cross-finding
  joins, this DSL is the wrong tool and OPA becomes the right answer.

Sources: <https://www.openpolicyagent.org/docs/latest/policy-language/> ·
<https://www.openpolicyagent.org/> — re-opened 30 September 2026.

**Note on version pinning.** The `yaml.safe_load` boundary is the load-bearing part here, not the
DSL's expressiveness. `!!python/object` makes PyYAML reach for `object.__new__`, so `safe_load` is
a security boundary in this repo, not a style preference.