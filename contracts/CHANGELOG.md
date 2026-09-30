# Contracts changelog

The contracts in this directory are frozen at `contracts-v1`. **A change is a team event**:
open a discussion, get a yes from the affected owners, add a row here, and only then edit.

An unannounced contract change invalidates every detector that was written against the old one,
and the resulting failures look like bugs in the detectors, not in the contract.

## Format

```text
## <version> — <date> — <one line>
- <what changed>
- <who it breaks>
- <who approved>
```

---

## contracts-v1 — 2026-09-30 — initial freeze

Day-1 contracts, tagged `contracts-v1`. Five contracts plus the report hand-off and the results
table.

| contract | owner | status |
|---|---|---|
| `FINDING.md` | P1 | frozen |
| `DETECTOR.md` | P1 | frozen |
| `MANIFEST.md` | P5 | strawman, **P5 edits** |
| `RECORD.md` | P4 | strawman, **P4 edits** |
| `EMBEDDINGS.md` | P2 | strawman, **P2 edits** |
| `MODEL_WRAPPER.md` | P3 | strawman, **P3 edits** |
| `REPORT_INPUT.md` | P4 renders, P1 writes | strawman |
| `RESULTS_TABLE.md` | P5 writes, P1 reads | strawman |
| `finding.schema.json` | P1 | frozen |
| `finding.draft.schema.json` | P1 | frozen |
| `policy.schema.json` | P1 | **lands Phase 3** |

### Decisions inside v1

| decision | note |
|---|---|
| JSON Schema **2020-12**, not Draft 7 | `if/then` and `$defs`. `Draft202012Validator` |
| `additionalProperties: false` at top level | unknown keys are bugs. Free JSON only in `metadata` |
| Flat optional fields, not a nested `subject` | policy matches top-level keys. A nested shape means every rule reaches through an object |
| 16-tag closed vocabulary | a new tag is a schema-version discussion, not a one-line addition |
| `sample_ids` caps at 50 | `sample_count` carries the true number. A 4000-id table cell is unreadable |
| `link_hints` required on trigger tags | a trigger finding with no geometry is a schema error, not a degraded link |
| `reconstructed` must not carry `patch_id` | carrying one fakes an identity match the detector never measured |
| Draft and final schemas differ by `id` only | detectors never hand-assign ids; the pipeline owns the sort |
| `limitations` min 10 chars, never empty | the honesty rule, enforced by the schema rather than by review |
| `severity` and `confidence` are independent | impact vs belief. Collapsing them loses the operational decision |
| `AuditContext` has no ground-truth attribute | a detector that reads truth reports a detection rate of 1.0 and tells nobody anything |
| Three functions on `ChainBackend` | `append`, `verify`, `head`. P4's day-4 drop-in has the same surface |
| Two report hashes | an HTML file cannot contain its own digest. `payload_sha256` in the header, `report_file_sha256` printed by the CLI |
| Core dependencies only | pydantic, PyYAML, jsonschema, typer, rich, numpy. torch/onnxruntime/cv2/faiss never import into `cvassure.core` |

### Acknowledgement

- [ ] **P1** — FINDING, DETECTOR, both schemas. **Acknowledged**
- [ ] **P2** — EMBEDDINGS, data-family results rows. **PENDING**
- [ ] **P3** — MODEL_WRAPPER, model-family results rows. **PENDING**
- [ ] **P4** — RECORD, REPORT_INPUT. **PENDING**
- [ ] **P5** — MANIFEST, RESULTS_TABLE. **PENDING**
- [ ] **PPT owner** — slide 3 reads FINDING/DETECTOR. **PENDING**

Tag `contracts-v1` only after all five are acknowledged. Until then the tag means "proposed",
and the day-1 message says so.
