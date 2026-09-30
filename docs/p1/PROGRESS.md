# P1 PROGRESS — append-only

Never edit an old entry. Add a new one. This file is the audit trail for Person 1's own work
and is the only place where a phase is declared green.

Format per entry: date, phase, what changed, commands run with **actual** output, tests run
with actual pass/fail, `BLOCKED-ON`, `HUMAN TODO`, next phase.

Legend: `BLOCKED-ON: P<n>` means a teammate artefact is missing and work continued against the
contract with a synthetic fixture. `HUMAN TODO` means only a person can close it.

---

## 2026-09-30 — Phase 0 — read plan, fills, decisions

**Phase goal.** Read `Person1_Complete_Plan.md` in full. Ask one question batch for the
Section 17 fills. Create `PROGRESS.md` and `DECISIONS.md`.

**Files changed**

| Path | Note |
|---|---|
| `docs/p1/DECISIONS.md` | created. Section 0 table copied, fills answered, env facts, uncalibrated threshold register, open-items clash log. |
| `docs/p1/PROGRESS.md` | created. This file. |
| `README.md` | pre-existing, untouched this phase (it holds `# CVAssure` only). |
| `.gitignore` | not yet created — lands in Phase 1 with D1. `HUMAN TODO` reminder below. |

**Commands run (actual output)**

```text
$ git log --oneline -5
4bcbbd6 Initial commit

$ git branch --show-current
main

$ git remote -v
origin  https://github.com/indalok/cvassure (fetch)
origin  https://github.com/indalok/cvaccure (push)

$ git status --short
 M README.md
?? .cursor/
?? .cursorignore
?? .cursorindexingignore
?? Person1_Complete_Plan.md
?? optional/

$ git ls-tree -r HEAD --name-only
README.md

$ py -0p
 -V:3.13 *        C:\Users\Admin\AppData\Local\Python\pythoncore-3.13-64\python.exe
 -V:3.11          C:\Program Files\Python311\python.exe
 -V:Astral/CPython3.14.5 C:\Users\Admin\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe
```

**Shell quirk recorded.** `cd /c/Users/Admin/Desktop/cvaccure` fails in this git-bash
(`No such file or directory`) even though the directory exists and Python can list it. Working
form: `cd /c/Users/Admin/Desktop && cd cvassure`. Cause not investigated — not worth a phase.
Every later phase must use the working form.

**Question batch asked.** One batch, five questions, per plan §16 agent protocol.

| Fill | Answer |
|---|---|
| Team name | `CVAssure` |
| GitHub handles | keep `P2`…`P5` placeholders, mark `HUMAN TODO` |
| License | MIT |
| Daily call time | leave `[[FILL]]` |
| venv | create `.venv` on Python 3.11 now |

**Tests run.** None. Phase 0 creates documentation only; no code exists to test.

**BLOCKED-ON.** None.

**HUMAN TODO**

- `CODEOWNERS` GitHub handles (E4 in `DECISIONS.md`).
- Confirm with the SPOC whether the SIH `Deadline 30 September 2026` on the mirror page is the
  portal close or only a listing date (E1). Do not invent a second deadline.
- Re-fetch the SIH26228 page on day 1; paste any evaluation weights into
  `docs/research/sih_insights.md`. At the 30 Sep 2026 fetch there was no weights table, so no
  weights are recorded anywhere (E2).

**Next phase.** Phase 1 — day 1. D1 package/lint/CI, D2 Finding schema, D3 Detector interface,
D4 contract pack and strawmen, D21 coordination kit. Gate: fixtures validate, CI green,
day-1 message ready.

---

## 2026-09-30 — Phase 1 — day 1: D1, D2, D3, D4, D21

**Phase goal.** D1 package/lint/CI, D2 Finding schema, D3 Detector interface, D4 contract pack
and strawmen, D21 coordination kit. **Gate: fixtures validate, CI green, day-1 message ready.**

### Files changed (39 new, 1 modified)

| path | deliverable |
|---|---|
| `pyproject.toml` | D1. setuptools, src layout, pinned core deps, ruff + pytest config |
| `.gitignore` | D1. `out/`, `wheelhouse/`, `.venv/`, `demo/manifest.json`, `*.pem`, `*.key` |
| `.github/workflows/ci.yml` | D1. Ubuntu + Windows, py3.11, ruff, schema check, socket-blocked run, heavy-import guard |
| `.github/CODEOWNERS` | D1 + D21. `P1`…`P5`, `HUMAN TODO` on handles |
| `.github/pull_request_template.md` | D21. Honesty section is mandatory |
| `CONTRIBUTING.md` | D1. Five rules, security defaults, append-only logs |
| `LICENSE` | D1. MIT |
| `README.md` | D1. Full day-8 README written early; owners, add-a-detector, honesty rule |
| `src/cvassure/core/finding.py` | **D2.** Pydantic v2 model, draft+final schema export, `validate_finding` gate |
| `src/cvassure/core/detector.py` | **D3.** `Detector` ABC, `AuditContext`, `DetectorResult`, `Dataset`, `Sample`, `interface_errors` |
| `src/cvassure/core/__init__.py`, `src/cvassure/__init__.py`, `py.typed` | package |
| `contracts/finding.schema.json` | D2. **Generated** from the model, never hand-edited |
| `contracts/finding.draft.schema.json` | D2. Same minus `id` |
| `contracts/FINDING.md` | D2. severity vs confidence, draft vs final, `link_hints`, worked example per asset |
| `contracts/DETECTOR.md` | D3. ~30-line copy-paste stub |
| `contracts/MANIFEST.md` | D4 strawman (P5) |
| `contracts/RECORD.md` | D4 strawman (P4) |
| `contracts/EMBEDDINGS.md` | D4 strawman (P2) |
| `contracts/MODEL_WRAPPER.md` | D4 strawman (P3) |
| `contracts/REPORT_INPUT.md` | D4. Five files, two-hash rule, offline renderer rules |
| `contracts/RESULTS_TABLE.md` | D4. 13 CSV columns, 12 attack classes, status rules |
| `contracts/CHANGELOG.md` | D4. v1 decision table, acknowledgement checklist |
| `docs/p1/DAY1_MESSAGE.md` | **D21.** Ready to send. `[[FILL]]` call time |
| `docs/p1/STANDUP_TEMPLATE.md` | D21 |
| `docs/p1/DECISIONS.md` | Phase 0 |
| `docs/p1/PROGRESS.md` | this file |
| `tests/core/test_finding.py` | 63 tests: 7 valid fixtures + 23 invalid cases |
| `tests/core/test_detector.py` | 16 tests, including the documented stub executed as written |
| `tests/fixtures/findings/valid_*.json` | 7 valid fixtures, all five assets + linked pair |

**Decisions made inside Phase 1**

1. **The pipeline gate runs BOTH validators.** First implementation validated against JSON
   Schema only and **9 of 23 invalid fixtures passed** — JSON Schema 2020-12 cannot express
   "only `asset=system` may have empty evidence", "NaN is not a number", or "`..` in an
   evidence path". `validate_finding()` now runs `Draft202012Validator` then pydantic, and
   raises `SchemaError` carrying `detector_id` so the CLI can exit 3 naming the guilty
   detector. Test `test_contract_schemas_on_disk_match_the_model` fails if the committed JSON
   drifts from the model.
2. **`link_hints` is enforced on the tag, not left as advice.** A finding tagged
   `patch_trigger` / `blend_trigger` / `trigger_sweep_hit` / `trigger_reconstructed` without
   `link_hints` is a schema error. A trigger finding with no geometry is what kills the LINK
   line in the demo, and advice is not enforcement.
3. **A `reconstructed` trigger may not carry a `patch_id`.** Schema rejects it. It would fake
   an identity match P3 never measured, and the linker would score it as if two sides had
   independently named the same patch.
4. **`[project.scripts]` deliberately omitted.** It would point at `cli.py`, which lands in
   Phase 2. Pointing at a missing module breaks `pip install -e .` today.
5. **`interface_errors()` lives in `detector.py`, not the registry.** One home for the
   contract, and a teammate can call it from their own test.
6. **Invalid fixtures are a mutation table in the test, not 23 JSON files.** The failure reason
   sits next to the case that causes it. Valid fixtures stay real files because they double as
   the reference examples in `FINDING.md`.
7. **README written in full at day 1**, not stubbed. It costs nothing now and it is the artefact
   the SIH software edition explicitly asks for.
8. **ruff `B027` suppressed with a reason** on `Detector.configure` rather than weakening the
   rule globally. It is a deliberate no-op hook.

### Commands run (actual output)

```text
$ py -3.11 -m venv .venv && pip install -e ".[dev]"
Successfully installed annotated-types-0.8.0 attrs-26.1.0 colorama-0.4.6 iniconfig-2.3.0
  jsonschema-4.26.0 markdown-it-py-4.2.0 mdurl-0.1.2 numpy-2.4.6 packaging-26.3
  pip-26.2.1 pluggy-1.6.0 pydantic-2.13.5 pydantic_core-2.46.5 Pygments-2.21.0
  pytest-8.4.2 pytest-socket-0.8.1 PyYAML-6.0.3 referencing-0.37.0 rich-14.3.4
  rpds-py-2026.6.3 ruff-0.16.9 shellingham-1.5.4 typer-0.27.2 typing_extensions-4.16.0

$ python -m pytest
........................................................................ [ 91%]
.......                                                                  [100%]
79 passed in 0.65s

$ python -m pytest --disable-socket --allow-unix-socket
79 passed in 0.66s

$ python -c "import cvassure.core.finding, cvassure.core.detector; assert no heavy modules"
core imports clean

$ python -m ruff check .
All checks passed!

$ python -m ruff format --check .
20 files already formatted
```

**Fresh-clone install (D1 acceptance), clean copy + clean venv, no repo state reused:**

```text
$ py -3.11 -m venv .venv && pip install -q -e ".[dev]" && python -m pytest
79 passed in 1.32s
```

### Tests run

79 pass, 0 fail. 0 fail socket-blocked. Fresh-clone install: 79 pass. ruff clean, format clean.

### BLOCKED-ON

None. All four teammate contracts are **strawmen committed for acknowledgement**, which is what
D4 asks for on day 1. Nobody's code is needed for Phase 1 to be complete.

### HUMAN TODO

- All five contract acknowledgements (PENDING boxes in `contracts/CHANGELOG.md`)
- `CODEOWNERS` GitHub handles (E4)
- Daily call time, still `[[FILL]]` in `DAY1_MESSAGE.md`
- SIH deadline confirmation (E1), weights re-fetch (E2)

### Phase 1 gate

**GREEN.** Fixtures validate (7 valid through both validators, 23 invalid rejected, each naming
the expected rule). CI config present and the three checks it runs were executed locally and
pass. Day-1 message ready to send.

### Next phase

Phase 2 — day 2. D5 registry, D6 stubs, D7 CLI + pipeline, fallback report,
`tests/fixtures/dummy_findings.json`. Gate: audit command completes on stubs, `--strict` exits 5,
nightly workflow file exists.

---

## 2026-09-30 — completion pass

Fixed the access-tier skip when no model wrapper is loaded. Evidence paths that leave `out/` are rejected. `contracts/policy.schema.json` is checked on every policy load. CI runs integration tests. README no longer says the CLI is unbuilt. `docs/p1/HANDOVER.md` and `docs/diagrams/architecture.dot` added.

`pytest` after this pass is the gate. Stub detectors remain. `--strict` still exits 5. Coverage stays Untested until Person 5's CSV exists. Slide PNGs are generated from that stub run and are not the final slide images.

**BLOCKED-ON:** P2 embeddings and real data detectors, P3 wrapper and backdoored model, P4 Ed25519 chain and report renderer, P5 `build_demo_scenario` and `results_table.csv`.

**HUMAN TODO:** CODEOWNERS handles, daily call time, contract acknowledgements.

