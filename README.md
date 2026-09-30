# CVAssure

Offline, CPU-only integrity assurance for training data, the model, and inference records
in a multi-contributor computer-vision pipeline.

One command audits all three, writes Findings in one schema, links a model trigger to the
contributor samples that carry the same patch, and writes a tamper-evident audit log plus an
offline HTML report. The coverage statement lists attack classes the tool does not support.

The spine runs today on day-2 stubs. `cvassure audit --strict` exits 5 until Persons 2-5
replace those stubs. Do not put a stub run on a slide.

Built for [SIH26228](https://sih2026.vuce.in/ps/SIH26228) — *Trustworthy Computer Vision
Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines*,
Ministry of Defence / Indian Army (DGIS), theme Blockchain & Cybersecurity.

---

## Install

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
```

Python 3.11. No GPU. No network needed after install.

## The command

```bash
cvassure audit --data ./demo/data --model ./demo/model.onnx --records ./demo/records
```

Output shape is fixed so it can be diffed between runs:

```text
[1/5] Load data (coco, offline) .............. ok       10000 images, 2 contributors
[2/5] Data integrity ......................... 1 finding    top source: C-07 (risk 0.90)
[3/5] Model integrity (white-box) ............ 1 finding    white-box trigger sweep hit
[4/5] Inference records ...................... 120 records  2 REJECTED (1 edited, 1 replayed)
[5/5] Shift assessment ....................... B-2: drift | B-3: manipulation
LINK  model trigger matches the patch seen in samples from C-07 -> severity escalated
DISPOSITION  data C-07: QUARANTINE | model: REVIEW | records: 2 REJECTED
Report: out/report.html (sha256 4f2a…)  Audit log: out/audit.log (chain verified)  Time: 0:12
```

*(Layout only. A real run prints numbers from that run, and a stub run prints a STUB line.)*

Other commands: `verify-log`, `verify-report`, `list-detectors`, `schema`, `coverage`, `doctor`,
`demo`. Full list in `Person1_Complete_Plan.md` §7.1.

## Offline install

For an air-gapped machine, build the wheelhouse once on a connected machine:

```bash
python scripts/make_offline_bundle.py
```

Then on the target:

```bash
pip install --no-index --find-links wheelhouse cvassure
```

`wheelhouse/` is gitignored. The audit command itself never opens a socket; a test runs the
whole pipeline with `socket.socket` disabled.

---

## Folder owners

| path | owner | contents |
|---|---|---|
| `src/cvassure/core/` | **P1** | schema, detector contract, registry, pipeline, CLI, policy, audit log, linking, coverage |
| `src/cvassure/data_integrity/` | P2 | embeddings, label flip, near-duplicate, OOD, spectral, source risk, adapters |
| `src/cvassure/model_integrity/` | P3 | wrapper + access tiers, fingerprint, weight digest, trigger sweep, reconstruction |
| `src/cvassure/provenance/` | P4 | signed records, hash chain, Merkle, HTML report, QR |
| `src/cvassure/shift/` | P5 | scenario builder, drift vs manipulation, metrics |
| `contracts/` | P1 writes, **owners edit** | frozen interfaces, day 1 |
| `docs/p1/` | P1 | decisions, progress, day-1 message, handover |

Enforced by `.github/CODEOWNERS`.

## Adding a detector

Subclass `Detector`, set five class attributes, return a `DetectorResult`. Full contract in
[`contracts/DETECTOR.md`](contracts/DETECTOR.md); the Finding contract is
[`contracts/FINDING.md`](contracts/FINDING.md).

```python
from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.finding import Finding


class MyDetector(Detector):
    id = "data.my_check"
    asset = "data"
    owner = "P2"
    version = "0.1.0"
    requires = frozenset()  # wrapper capabilities you need

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult(summary="no signal")
        # res.findings.append(Finding.draft(...))
        return res
```

Register it in your `pyproject.toml`:

```toml
[project.entry-points."cvassure.detectors"]
my_check = "cvassure.data_integrity.my_check:MyDetector"
```

and list the module in `configs/demo.yaml` so the load order is explicit and reproducible. A
real module always wins over the day-2 stub with the same id.

## Regenerating the demo

```bash
cvassure demo                              # P5's build_demo_scenario(seed=42)
cvassure audit --data ./demo/data --model ./demo/model.onnx --records ./demo/records --strict
```

If `build_demo_scenario` is not importable yet, `cvassure demo` prints `BLOCKED-ON: P5` and
exits 2. That is the honest answer, not an error.

---

## The honesty rule

**The coverage statement lists the attack classes CVAssure does not support, and that list is
part of the deliverable, not a footnote.** Three are declared `Unsupported` from the start and
stay that way unless we change config and write a changelog line:

- **Adaptive attackers** — an attacker who knows our detectors.
- **Imperceptible clean-label perturbations** — not detected by current methods.
- **Hardware / compiler backdoors** — out of scope.

Everything else is `Untested` until a measurement exists. A class with no row is `Untested`,
never `Supported`. A high-severity finding with no matching policy rule gets the default
`review`, never a silent `accept`.

Related, and enforced in code rather than in this file:

- **Offline and air-gapped.** No cloud API, no CDN, no telemetry.
- **Data is synthetic or public-licence.** No classified, operational, or service-generated
  data, in fixtures, demos, or docs. This is the problem statement's dataset rule.
- **The baseline assessment never retrains the submitted model.**
- **White-box methods skip honestly.** If the model is black-box, the method is reported
  unavailable — it never pretends to have run.
- **A crash is a finding.** A detector that raises produces an `asset=system` Finding naming it.
  A missing method is never a clean result.
- **No invented numbers.** Every printed value was computed in that run. Thresholds are marked
  `UNCALIBRATED` in `docs/p1/DECISIONS.md` until they are fitted on data with negative controls.
- **No hard-coded contributor or class ids** in policy, linker, or core. The demo story appears
  because the inputs contain it.

## Data formats

COCO JSON and YOLO txt in, ONNX or PyTorch/TorchScript model in, JSON Lines inference records
in. Not hard-coded to one architecture or one dataset. Day-2 adapters are thin readers that
build an internal sample table; Person 2 owns the full adapters and may replace them.

## Development

```bash
pytest                      # unit + integration
ruff check . && ruff format --check .
pytest --disable-socket      # proves the audit path needs no network
```

CI runs Ubuntu and Windows on Python 3.11. Nightly regenerates seed 42 and audits it. The
uploaded `out/` artefact is the regression diff.

## Licence

MIT. See [`LICENSE`](LICENSE).
