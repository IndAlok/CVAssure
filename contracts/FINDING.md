# The Finding object

**Owner:** Person 1. **Status:** frozen for `contracts-v1`. **Dialect:** JSON Schema 2020-12.

One assurance flag. Every detector, on every asset, returns this shape. There is no second
shape and no ad-hoc dict, because the whole governance layer — policy, linking, the audit log,
the report — reads only this.

Read this before you extend anything. A change here is a team event, not a PR.

---

## 1. Draft vs final

There are two schemas and they differ in exactly one property.

| | `contracts/finding.draft.schema.json` | `contracts/finding.schema.json` |
|---|---|---|
| who builds it | a detector | the pipeline |
| `id` | absent | present, `^F-\d{3,}$` |
| `detector` | absent | filled by the pipeline |
| `escalation`, `policy` | absent | filled by the linker and policy engine |
| `linked_findings` | empty | filled by the linker |

**Pipeline order matters.** Validate every finding against the *final* schema **before**
linking. If you link first, a bad finding from a third-party plugin has already mutated its
neighbours and you cannot tell which field was the bad one. The pipeline aborts with exit
code 3 and names the detector that emitted the invalid finding.

**Do not hand-assign an id.** `Finding.draft()` refuses an `id` argument on purpose. Ids are
assigned by the pipeline so that the sort in §7.2 of the plan is the only thing that decides
`F-001` ordering. Two people picking their own ids is how you get a report where the numbers
do not match the rows.

---

## 2. severity vs confidence

They are independent axes and you must not use one for the other.

| field | question it answers | who sets it |
|---|---|---|
| `severity` | *if this finding is true, how bad is it?* | detector, from domain knowledge |
| `confidence` | *how sure am I that it is true?* | detector, from its own calibration |

A catastrophic finding you are unsure about is `severity: 0.95, confidence: 0.25`. A trivial
finding you are sure about is `severity: 0.1, confidence: 0.9`. Policy reads both, separately
— a high-severity low-confidence flag and a high-severity high-confidence flag are not the same
operational decision, and collapsing them into one "score" throws that away.

**`severity` is impact, not risk.** Do not multiply by prevalence, do not fold in how many
samples were affected, do not raise it because the contributor is important. If you need a
source-level rollup, the numbers belong in `metadata` and the rollup belongs in `reason`.

Each detector documents how it calibrates `confidence` in `docs/p1/` or its own module
docstring. A detector that cannot say how it calibrated confidence has not met the contract.

---

## 3. The fields

### Required, always

| field | rule | note |
|---|---|---|
| `schema_version` | const `"1.0"` | bump only with a changelog line and a team message |
| `id` | `^F-\d{3,}$` | pipeline-assigned, absent on drafts |
| `asset` | `data` \| `model` \| `records` \| `shift` \| `system` | see below |
| `reason` | 10–300 chars, **one line** | must contain the measured value when one exists |
| `evidence` | relative paths under `out/evidence/` | min 1, except `asset=system` |
| `severity` | `[0, 1]`, not NaN, not Inf | |
| `confidence` | `[0, 1]`, not NaN, not Inf | |
| `access_level` | `white-box` \| `gray-box` \| `black-box` \| `not-applicable` | |
| `limitations` | min 10 chars, **never empty** | the honesty rule |
| `disposition` | `accept` \| `review` \| `quarantine` \| `rejected` | policy overwrites yours |
| `linked_findings` | array of finding ids | linker fills it |

`additionalProperties: false` at the top level. An unknown key is rejected, not ignored.

**`reason` is one line.** A newline is a validation error. Put detail in `metadata`, and put
what you could not do in `limitations`. The CLI prints `reason` inline; a wrapped paragraph
breaks the fixed terminal layout.

**`evidence` is relative to `out/`.** `evidence/foo.png` means `out/evidence/foo.png`.
Absolute paths, Windows drive letters, backslashes, and any `..` component are rejected. The
pipeline additionally resolves each path and records its sha256, so an evidence file that
does not exist is caught before the report is written.

**`limitations` is not optional and not a formality.** "Empty is a schema error" is the rule
that stops a detector claiming more than it checked. Write what you did *not* do: the attack
families you cannot see, the calibration you never fitted, the evidence you lacked.

### `asset`

| value | means | who emits |
|---|---|---|
| `data` | training data, sample-level or source-level | P2 |
| `model` | the model file, or the wrapper's behaviour | P3 |
| `records` | inference records and their chain | P4 |
| `shift` | distribution shift on a batch | P5 |
| `system` | a detector crashed or was skipped, and that fact must still be visible | pipeline |

`shift` is its own asset, not a kind of `data`. Folding it in makes "which asset was affected"
unanswerable in the report.

`system` is the only asset that may carry empty `evidence`, because in that case the error
*is* the evidence. It is also the only asset the pipeline writes without a detector asking.

### Optional, fixed names

| field | type | note |
|---|---|---|
| `detector` | `{id, version, owner}` | pipeline fills it |
| `source_id` | string | contributor id, e.g. from a sidecar. Never hard-coded in core |
| `batch_id` | string | |
| `class_label` | integer or string | |
| `sample_ids` | array, **cap 50** | the cap is real; truncate and put the true count in `sample_count` |
| `sample_count` | integer ≥ 0 | the untruncated number |
| `tags` | array from the closed vocabulary below | |
| `link_hints` | see §4 | required on trigger findings |
| `escalation` | `{escalated, severity_before, linked_to, method}` | linker only |
| `policy` | `{rule_id, policy_hash}` | policy engine only |
| `stub` | bool, default `false` | a stub sets `true` and prefixes `reason` with `[STUB]` |
| `metadata` | object | free JSON. **the only place an unknown key is allowed** |

`sample_ids` caps at 50 because a source-level finding can touch thousands of samples and a
report row that lists 4000 ids is unreadable. Set `sample_count` to the truth and truncate
`sample_ids`.

### Tag vocabulary — closed set

```
patch_trigger              blend_trigger            label_flip
near_duplicate             ood                      fingerprint_mismatch
weight_digest_mismatch     trigger_sweep_hit        trigger_reconstructed
verification_failed        replay                   substitution
drift                      manipulation             undetermined
skipped_access_tier
```

No other value is valid. Adding one is a schema-version discussion because report consumers
switch on these strings.

Use `undetermined` when you genuinely cannot tell, and `skipped_access_tier` when the method
did not run because the model tier did not allow it. Those two tags are the difference between
"CVAssure looked and found nothing" and "CVAssure could not look", and the coverage statement
depends on telling them apart.

---

## 4. `link_hints` — the evidence, never the verdict

The cross-asset linker decides whether a model trigger and a data patch are the same visual
trigger. It may only use `link_hints`. It does not get to look at your arrays, your metadata
or the ground truth, and it must be able to print nothing.

**Required** on any data finding tagged `patch_trigger` or `blend_trigger`, and on any model
finding tagged `trigger_sweep_hit` or `trigger_reconstructed`. A trigger finding with no
geometry is a schema error, not a degraded link.

```json
"link_hints": {
  "target_class": 0,
  "source_id": "only on data findings",
  "trigger": { "kind": "patch_library", "patch_id": "P-03" },
  "location_bbox": [0.1, 0.1, 0.3, 0.3],
  "patch_template_path": "evidence/relative.png"
}
```

| field | who | rule |
|---|---|---|
| `target_class` | P2, P3 | the class the trigger targets. Both sides must agree or the score is 0 |
| `source_id` | P2 only | rejected on a non-data finding |
| `trigger.kind` | P2, P3 | `patch_library` or `reconstructed`, nothing else |
| `trigger.patch_id` | P2 with `patch_library` | the identity component. Required for that kind |
| `trigger.mask_path` | P3 with `reconstructed` | required for that kind |
| `trigger.pattern_path` | P3 | optional, the pattern image for NCC |
| `location_bbox` | P2, P3 | `[x, y, w, h]`, normalised 0–1, **origin top-left** |
| `patch_template_path` | P2, P3 | relative path, same rules as `evidence` |

**A `reconstructed` trigger must not carry a `patch_id`.** The schema rejects that
combination. Carrying one would let P3 claim an identity match it never measured, and the
linker would score it as if two sides had independently named the same patch. Reconstruction
produces a mask and an optional pattern; identity comes from a patch library.

Bboxes are normalised and top-left origin because datasets disagree on pixel counts and image
orientation. If your detector works in pixel space, normalise before you build the object.

**What the linker does with this** (so you can emit the right evidence):

1. Classes differ on both sides → score 0, stop.
2. `identity` — 1 if `patch_id` equal, absent if either side lacks it.
3. `overlap` — IoU of the two bboxes, or of reconstructed-mask support vs data bbox.
4. `pattern` — max normalised cross-correlation between the masked pattern and the template.
5. Renormalise the configured weights over the components that exist, link if ≥ `tau_link`.

**Emit the evidence you actually have.** A black-box sweep has `patch_id` and class and
nothing else. Emit that. The linker will link on identity alone and will set the model
finding's `limitations` to say pattern similarity was not available. Padding `link_hints` with
a bbox you guessed is how a false link gets into a demo.

---

## 5. `escalation` and `policy` are not yours

| field | written by | what it means |
|---|---|---|
| `escalation` | the linker | model severity was raised by noisy-OR once a link existed. `severity_before` keeps the pre-link value so the report can show what changed |
| `policy` | the policy engine | which rule set `disposition`, and the sha256 of the policy file that decided it |

If you write either field, the report will claim a decision nobody made. Leave them `None`.

---

## 6. Adapter field names (plan §4)

The day-2 adapters build an internal sample table: `sample_id`, `path`, `class_id`,
`source_id`, `batch_id`.

Contributor and batch come from **extra annotation fields in the dataset file** or from a
**sidecar JSON** that is *not* the ground-truth attack manifest. COCO puts them wherever the
contributor put them; the thin readers look at, in order, the annotation fields
`contributor_id` / `source_id` / `batch_id`, then a sidecar named by `--sidecar`. P2 owns the
full adapters and may replace the day-2 readers wholesale.

Never read Person 5's `MANIFEST.md` ground truth from inside `cvassure audit`. Only coverage
and evaluation code may. That is what keeps the detection numbers meaningful.

---

## 7. Worked examples

The committed fixtures under `tests/fixtures/findings/` are the canonical examples and the
tests validate every one of them.

### data — a patch in one contributor's samples

`tests/fixtures/findings/valid_data_patch.json`. Sample-level evidence aggregated to a
source: `source_id` set, `sample_ids` lists the three affected samples, `sample_count` is the
real count, `link_hints.trigger.patch_id` is `P-03`, `location_bbox` is normalised, and
`limitations` names the library's blind spot. `severity` 0.9 because a live trigger in
submitted data is bad if true; `confidence` 0.85 because patch matching is exact-match-ish and
calibrated on the seeded scenario.

### model — a white-box trigger sweep, linked to that data

`tests/fixtures/findings/valid_model_sweep_linked.json`. This is mock-up 1C, F-019, linked to
F-001. Note four things: `link_hints.trigger.kind` is `reconstructed` with a `mask_path` and
**no** `patch_id`; `escalation.severity_before` (0.71) is lower than the escalated
`severity` (0.95) so a reader can see the link did the raising; `disposition` is `review`, not
`quarantine`, because the policy rule for a linked model finding says review; and
`limitations` names the method (Neural Cleanse style) and says no retraining happened.

### records — an edited record, and a replayed one

`valid_records_edited.json` and `valid_records_replay.json`. Both are `disposition: rejected`
because a record that fails verification is not a judgement call. The replay one carries two
tags: `replay` says what happened, `verification_failed` is what the policy rule keys on. The
`limitations` on the replay fixture says the detection only holds inside the logged window,
which is true and is the kind of sentence this field exists for.

### shift — fog and a patch, on two batches

`valid_shift_drift.json`: `tags: ["drift"]`, low severity, `accept`, PSI/MMD/KS in `metadata`.
`valid_shift_manipulation.json`: `tags: ["manipulation"]`, higher severity, `quarantine`,
spectral peak in `metadata`. Different batch ids. The distinction is the point of PS §2.2.4
and the pair is the proof the distinction is computed rather than asserted.

### system — a detector crashed

`valid_system_crash.json`. `asset: system`, `evidence: []` (the only asset allowed that),
`confidence: 1.0` because the crash is certain, `severity: 0.2` because a missing method is not
an attack, `tags: []`, and `limitations` says in plain words that the method did not run at
all. A crash must never be silent and must never look like a clean result.

---

## 8. Checklist before you open a PR

- [ ] `Finding.draft(...)`, no `id`
- [ ] `reason` is one line, 10–300 chars, and contains the measured number
- [ ] `evidence` paths are relative, no `..`, and the files exist under `out/evidence/`
- [ ] `severity` and `confidence` set independently, both in `[0, 1]`
- [ ] `limitations` says what you did not check, in a sentence a judge could quote
- [ ] `tags` from the closed vocabulary; `link_hints` present on any trigger tag
- [ ] `escalation` and `policy` left `None`
- [ ] `schema_version` left at `"1.0"`
- [ ] a test asserts your finding validates, and one asserts your rejection case fails
