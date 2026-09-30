# Day 1 message — send this to the team, then tag `contracts-v1`

Owner: Person 1. Sent 2026-09-30. This is the whole hand-off. Read it once, then work from
`contracts/`.

---

## 1. What we are building

One offline, CPU-only command that audits three assets and produces one auditable answer.

```text
cvassure audit --data ./demo/data --model ./demo/model.onnx --records ./demo/records
```

It loads contributed data, the model and the inference records; every detector returns **one
Finding shape**; a linker decides whether the model trigger is the same trigger seen in one
contributor's samples; a policy file turns each finding into a disposition; the whole run is
written to a hash-chained audit log; and a self-contained HTML report lands in `out/`.

No cloud, no CDN, no telemetry. The judge will pull the network cable and the demo must still
work. That is PS §2.2.6, not a preference.

**Repo:** https://github.com/indalok/cvassure
**License:** MIT. **Python:** 3.11. **Package:** `cvassure`.

---

## 2. Who owns what

| # | owns | PRs touch |
|---|---|---|
| 1 | schema, detector contract, CLI, policy, audit log, linking, coverage, repo/CI, two PPT images | `src/cvassure/core/`, `contracts/`, `policies/`, `configs/`, `tests/core/`, `docs/p1/` |
| 2 | data integrity: embeddings, label flip, near-duplicate, OOD, spectral, source risk, COCO/YOLO adapters | `src/cvassure/data_integrity/` |
| 3 | model wrapper + access tiers, fingerprint, weight digest, trigger sweep, reconstruction | `src/cvassure/model_integrity/` |
| 4 | signed records, hash chain, Merkle, tamper/replay tests, offline HTML report, QR, demo video | `src/cvassure/provenance/` |
| 5 | `build_demo_scenario(seed=42)`, drift vs manipulation, metrics table | `src/cvassure/shift/` |

`.github/CODEOWNERS` enforces it. Do not edit another person's folder; open an issue instead.

**Branches:** `p2/*`, `p3/*`, `p4/*`, `p5/*`. Never commit to `main` directly.
**PR size:** under 400 lines. If it is bigger, split it — a big PR gets a rubber stamp and that
is how a contract breaks silently.
**Daily call:** `[[FILL]]` — 15 minutes, standup template in `docs/p1/STANDUP_TEMPLATE.md`.

---

## 3. The five contracts, and what each of you must emit

Everything in `contracts/` is frozen at `contracts-v1`. Read the one that owns your output.
A contract change is a team discussion, not a PR.

### P2 — data integrity

Read `contracts/FINDING.md` and `contracts/EMBEDDINGS.md`.

You emit Findings on `asset: data`. Three things are non-negotiable:

1. **`link_hints` on every `patch_trigger` and `blend_trigger` finding.** `trigger.patch_id`
   from your patch library, `location_bbox` normalised `[x, y, w, h]` in 0–1 with origin
   top-left. Without geometry there is no LINK line in the demo.
2. **Source-level aggregation.** PS §2.2.1 wants sample evidence rolled up to a source risk,
   not a list of isolated samples. Set `source_id` and `sample_count`; `sample_ids` caps at 50.
3. **Embeddings** as a NumPy array + sample ids sidecar. Day 1 is the layout, not the encoder.

### P3 — model integrity

Read `contracts/FINDING.md` and `contracts/MODEL_WRAPPER.md`.

You emit Findings on `asset: model`, and the wrapper is the gate for everyone else's work.

1. **`link_hints` on every `trigger_sweep_hit` and `trigger_reconstructed` finding.** Use
   `kind: "reconstructed"` with a `mask_path` and **no `patch_id`** — the schema rejects a
   reconstructed hint that claims an identity match.
2. **A backdoored demo model by the end of week 1.** This is the single biggest risk to the
   demo. Without it the linker has nothing real to match and the LINK line is missing. Say the
   moment you have it, not at the end of the week.
3. **`declare_access_tier()` and `capabilities()` must agree.** A missing capability returns a
   typed `Unavailable`, never a zero array. A zero-filled gradient tensor produces a real-looking
   "nothing found", which is the worst possible failure in an integrity tool.

### P4 — provenance and the report

Read `contracts/RECORD.md` and `contracts/REPORT_INPUT.md`.

1. **Chain API by day 4**, three methods: `append`, `verify`, `head`. Same surface as my
   day-2 `LocalSha256Chain`, so swapping yours in changes nothing else. Until then we run
   without signatures and nothing blocks.
2. **`render_report(out_dir) -> Path` by day 6.** It reads `findings.json`, `quarantine.json`,
   `coverage.json`, `run_manifest.json`, `link_report.json` and `evidence/` — and nothing else.
   No network, inline CSS only, no CDN. I keep a fallback HTML behind a missing-import check so
   the day-2 pipeline still produces a report.
3. **The demo video is yours, and it must not be AI-generated.** The SIH software-edition
   guidance requires the video and its narration to be delivered by team members. I am not
   building one and nobody should use a TTS voice-over.
4. **Record fields** as in `RECORD.md`, signed over canonical JSON that includes `prev_hash`.

### P5 — the scenario

Read `contracts/MANIFEST.md` and `contracts/RESULTS_TABLE.md`.

1. **`build_demo_scenario(seed=42)` by end of day 2.** Until it lands I run on a hand-made
   fixture so the pipeline is never the thing that is late. Do not design a second scenario
   format.
2. **The results CSV columns** are in `RESULTS_TABLE.md` and frozen. Twelve `attack_class`
   values. `n_seeds >= 3` for anything to read as Supported. `false_alarm_rate_mean` is on a
   clean control and is the column that decides credibility.
3. **Four link variants**, same seed family: patch equals data patch (link), patch differs (no
   link), clean model with poisoned data (no link), backdoored model with clean data (no link).
   The negatives are the measurement.
4. **Synthetic or public-licence data only.** No classified, operational or service-generated
   data — that is the PS rule, and `MANIFEST.json` carries a `synthetic: true` flag to prove it.
5. Attack families: BadNets-style patch, blend, label flip, near-duplicate flood, OOD insertion,
   model swap, record tamper/replay, natural fog. Cite TrojAI and BackdoorBench for the
   *definitions*; do not install either repo or download their weights.

---

## 4. The rules, short

1. **Never invent a number.** Mock-up values like `0.xx` and `xx%` are layout, not results.
   Print a value only if this run computed it. This is the rule that decides whether a judge
   trusts the rest of it.
2. **No hard-coded contributor id, class id or dataset name** in policy, linker or core. The
   demo story appears because the *inputs* contain it. `C-07` is a fixture value, not a
   constant.
3. **No ground truth in the audit path.** Nothing under `src/cvassure/` reads
   `MANIFEST.md`. Evaluation and coverage code may. A detector that reads the answers reports a
   detection rate of 1.0 and means nothing.
4. **Offline.** No sockets in the audit path. A test runs the whole thing with `socket.socket`
   disabled. Do not add a dependency that wants the network at import time.
5. **Stubs are loud and temporary.** A stub sets `stub: true`, prefixes `reason` with
   `[STUB]`, and shows a STUB badge. When you land the real detector, **keep the same detector
   id** so the registry prefers it over the stub, and delete the stub in the same PR.
6. **Thresholds live in config** and are marked `UNCALIBRATED` in `docs/p1/DECISIONS.md` until
   we fit them on seeded data that includes negative controls.
7. **`limitations` is mandatory and is never a formality.** Say what you did not check.
8. **Commits are small and separate.** One concern per commit, tests with each unit. No
   secrets, no `out/`, no `wheelhouse/`, no large binaries.

---

## 5. Checkpoints

| day | gate | who |
|---|---|---|
| 2 | stub pipeline runs end to end; `--strict` exits 5 | P1 |
| 4 | first real detectors merged; chain API and wrapper in place | P2, P3, P4 |
| 6 | full demo scenario, backdoored model, real link, real report | all |
| 8 | feature freeze, images sent to the PPT owner | P1 + P5 |
| 9–10 | fixes and rehearsal only. No new features | all |

If you are going to be late, **say so in standup the same day.** A block longer than a few
hours gets said out loud. I will not chase anyone; I will write `BLOCKED-ON: P<n>` and keep the
spine moving against the contract.

---

## 6. Acknowledge

Read your contract, reply in the team thread with "read", and list anything you disagree with.
Once all five are in, I tag `contracts-v1` and it stops moving.

- [ ] P2 — read FINDING + EMBEDDINGS
- [ ] P3 — read FINDING + MODEL_WRAPPER
- [ ] P4 — read RECORD + REPORT_INPUT
- [ ] P5 — read MANIFEST + RESULTS_TABLE
- [ ] PPT owner — read FINDING (slide 3 depends on it)

Questions to me, not to the group. Thread noise on a frozen contract is how a decision gets
made twice and implemented once.
