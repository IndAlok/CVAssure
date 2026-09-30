# REPORT_INPUT — what Person 4 reads to render the report

**Owner:** Person 4 renders it. **Person 1 writes it.** Frozen shape, `contracts-v1`.

The audit command writes five things into `out/` and nothing else. `render_report(out_dir)`
may read **only that directory**. No network, no repository access, no import of the pipeline,
no re-running a detector.

---

## 1. The files

```text
out/
  findings.json        # array of final Findings, sorted, ids assigned
  quarantine.json      # sources / samples / batches to pull, with the findings that caused it
  coverage.json        # coverage statement, status per attack class
  run_manifest.json    # the run: seed, versions, hashes, timings, per-rule hits
  link_report.json     # every link considered, with components and scores
  evidence/            # images and JSON referenced by findings
  audit.log            # JSON Lines, hash-chained  (P1's, you display it)
```

`render_report(out_dir: Path) -> Path` returns the path of the HTML it wrote.

---

## 2. `findings.json`

An array of Finding objects, exactly as in `contracts/finding.schema.json`. No wrapper object,
no envelope, no pagination. Validate against the schema before you render; a finding that does
not validate is a bug in my pipeline, and you should fail loudly rather than render a partial
report.

Every field is populated except `escalation` and `policy` when nothing happened. **Do not
recompute `disposition`** — policy already decided it. Do not re-link. Display what is there.

Things the report must show, because the PS asks for each of them:

| requirement | field |
|---|---|
| human-readable reason | `reason` |
| supporting evidence | `evidence` (relative paths under `out/evidence/`) |
| confidence **or** severity | both, as separate columns |
| the affected asset | `asset` |
| recommended disposition | `disposition` |

And the two that are easy to lose: `limitations` on every row, and the `Unsupported` rows of
the coverage statement. A report that shows only what was found, with no statement of what was
not, fails PS §2.2.5.

---

## 3. `quarantine.json`

One file so your export button has one input.

```json
{
  "sources":  [{ "source_id": "C-07", "finding_ids": ["F-001"], "reason": "..." }],
  "samples":  [{ "sample_id": "s-0001", "finding_ids": ["F-001"] }],
  "batches":  [{ "batch_id": "B-3", "finding_ids": ["F-060"], "reason": "..." }],
  "records":  [{ "record_id": "rec-0007", "finding_ids": ["F-031"] }]
}
```

Built from findings whose `disposition` is `quarantine` or `rejected`. **`rejected` is in this
file, not in a separate one** — a failed record has to be actionable too, and it is.

Ids may repeat across a sample and its source; that is intended. `sample_ids` caps at 50 per
finding, so for a large source use `sample_count` for the headline and treat the id list as a
sample. Say "and N more" in the UI rather than implying the list is complete.

---

## 4. `coverage.json`

```json
{
  "generated_at": "2026-09-30T09:20:11Z",
  "status_counts": { "Supported": 0, "Partial": 0, "Untested": 9, "Unsupported": 3 },
  "rows": [
    {
      "attack_class": "Patch / blend trigger in data",
      "status": "Untested",
      "measured": null,
      "access_levels": [],
      "n_seeds": 0,
      "limitations": []
    }
  ],
  "assumptions": ["..."],
  "limitations": ["..."],
  "thresholds": { "T_support": 0.8, "T_far": 0.05, "min_seeds": 3, "calibration": "UNCALIBRATED" }
}
```

`measured` is `"0.92 ± 0.03 (5 seeds, synthetic-s42)"` — mean ± std, seeds, dataset. **Never
a bare percentage and never `TBD` presented as a rate.** If there is no row, `measured` is
`null` and `status` is `Untested`. Three classes are `Unsupported` by declaration and a
measured row must never flip them; if one later becomes measurable that is a config change and
a changelog line, not a silent edit.

`thresholds.calibration` says `UNCALIBRATED` until the values are fitted on seeded data with
negative controls. The judge will ask. Better to say it than to be caught.

---

## 5. `run_manifest.json`

| key | why you need it |
|---|---|
| `seed` | the run is reproducible only with the seed |
| `tool_version`, `git_commit` (`"unknown"` if absent) | which code produced this |
| `config_hash`, `policy_hash` | the exact config and policy, canonical sha256 |
| `input_hashes` | dataset manifest, model digest, records digest |
| `payload_sha256` | **the hash to show in the header and encode in the QR** |
| `report_file_sha256` | filled by P1 after you return, not by you |
| `audit_head` | the audit log chain head, so the footer can say `chain verified` |
| `stages` | per stage: status, timing, detector count, skip reason |
| `skipped_detectors` | id, reason, and the tier that blocked it |
| `stub_flags` | any detector that was a stub; drives the STUB badge |
| `policy_rule_hits` | `{rule_id: count}`, for a "why this disposition" column |
| `link_summary` | links created, threshold, weights |
| `timings` | per stage and total, seconds, float |

`payload_sha256` is the canonical-JSON sha256 of findings + coverage + run manifest, with the
manifest's own `payload_sha256` field excluded from the preimage.

**Two hashes, and the reason matters.** An HTML file cannot contain its own digest, so:

1. `payload_sha256` — of the *data*. This goes in the report header and the QR code.
2. `report_file_sha256` — of the *rendered HTML bytes*. I compute it after you return, log it,
   and the CLI prints it. The HTML does not need to contain it.

If you are tempted to "fix" this by having the page print its own hash, you will get a
different value every time you embed it, and `cvassure verify-report` will fail.

---

## 6. `link_report.json`

```json
{
  "tau_link": 0.5,
  "weights": { "identity": 0.5, "overlap": 0.2, "pattern": 0.3 },
  "calibration": "UNCALIBRATED",
  "links": [
    { "data_finding": "F-001", "model_finding": "F-019", "score": 0.91,
      "components": { "identity": 0.0, "overlap": 0.86, "pattern": 0.88 },
      "weights_used": { "overlap": 0.4, "pattern": 0.6 },
      "escalated": true, "severity_before": 0.71, "severity_after": 0.95,
      "evidence": "evidence/LINK_F-019_F-001.png" }
  ],
  "pairs_considered": 12,
  "pairs_linked": 1
}
```

`weights_used` is shown because weights are **renormalised over the components that exist**.
A black-box link has only identity, so it was scored with weight 1.0 on identity, not 0.5.
Printing the configured weights next to the actual ones is the difference between an honest
score and a suspicious one.

`pairs_considered` matters as much as `pairs_linked`. One link out of twelve pairs is a
result. Twelve links out of twelve is a linker that always says yes.

**Render this as "the model trigger matches the patch seen in samples from `<source_id>`", and
show the score.** If no link cleared the threshold, print nothing — that is a correct result
and the report should say so rather than omit the section.

---

## 7. Constraints on the renderer

- **Inline CSS and inline SVG only.** No CDN, no remote font, no remote image, no external
  `<script src>`. The report must open from a `file://` URL on a machine with no network. A
  test greps the generated HTML for `http://` and `https://` asset URLs.
- **No network calls at all**, and do not import `cvassure.core` to get a value — read the
  files. That is what keeps the report reproducible from the artefacts alone.
- **Escape every string** that came from a detector's `reason` or a contributor id. They are
  analyst-supplied text and may contain `<`, `&` and quotes.
- Evidence images are relative paths under `out/evidence/`. Resolve them relative to `out/`.
- Read `out/evidence/` only. Never follow a path from a finding outside `out/`; the schema
  rejects `..` and absolute paths, and you should not paper over that.

---

## 8. Fallback until your renderer lands

Day 2 I write a minimal inline-CSS HTML file with a findings table, a disposition line, the
coverage fragment and the payload hash, behind a missing-import check. The day-2 pipeline must
still produce `out/report.html`.

When yours lands, I call `render_report(out_dir)` if it imports, and otherwise fall back.
Your PR replaces the fallback; it does not add a flag. If it is ready before day 6, good; if
not, the fallback stands and the demo still runs.

---

## 9. Acknowledgement

Tagging `contracts-v1` confirms the five files, the two-hash rule, and the offline constraint.

- [ ] **P4** — renders from these files alone, offline, inline assets. **PENDING day 1**
- [ ] **P1** — writers, two-hash rule, fallback behind a missing-import check. Acknowledged
- [ ] **P5** — `coverage.json` comes from your results table. **PENDING**
