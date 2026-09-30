# CVAssure

Offline, CPU-only integrity checks for training data, a model, and inference records in a multi-contributor computer-vision pipeline.

One command audits all three. It writes findings in one schema, links a model trigger to contributor samples that carry the same patch, and writes a tamper-evident audit log plus an HTML report that does not fetch anything from the network. The coverage statement lists attack classes the tool does not support.

The built-in detectors are stubs. `cvassure audit --strict` exits 5 while any stub runs. A stub sets `stub` to true and starts its reason with `[STUB]`. Replace a stub by registering a real detector with the same id.

The audit does not open a socket, does not call a cloud API, and does not send telemetry. It does not retrain the submitted model. Data used with it must be synthetic or under a public licence. Do not put classified, operational, or service-generated data in fixtures or in a run.

## Install

Python 3.11.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

On Linux or macOS, activate with `source .venv/bin/activate`.

After install, the audit command does not need a network.

## Audit

```bash
cvassure audit --data ./data --model ./model.onnx --records ./records.jsonl
```

Inputs are a COCO JSON or YOLO txt dataset, an ONNX or TorchScript model, and JSON Lines inference records. The tool is not tied to one architecture or one dataset.

`--access` is `white-box`, `gray-box`, or `black-box`. A detector whose `requires` set is not covered by the wrapper is skipped and is not called. If no wrapper is loaded, the same skip applies.

`--strict` exits 5 when a stub ran. `--fail-on review`, `--fail-on quarantine`, or `--fail-on rejected` exits 10 when a finding has that disposition. `--reproducible` freezes timestamps so `findings.json` and `payload_sha256` match across runs. The CLI still prints the wall-clock time.

Other commands:

- `verify-log` checks the audit log hash chain.
- `verify-report` checks the two report hashes.
- `list-detectors` prints the loaded detectors.
- `schema` prints the Finding JSON Schema.
- `coverage` builds the coverage statement from a results CSV.
- `doctor` reports the local environment.
- `demo` calls `cvassure.shift.scenario.build_demo_scenario` when that function exists. If it does not, the command exits 2.

Exit codes:

- 0, the run finished.
- 2, usage or config error.
- 3, a detector or schema check failed.
- 4, audit log or report verification failed.
- 5, `--strict` and a stub ran.
- 10, `--fail-on` matched a disposition.

`--strict` is checked before the other failure codes.

## Output

A run writes these files under `--out`, which defaults to `out/`:

- `findings.json`
- `quarantine.json`
- `coverage.json`
- `run_manifest.json`
- `link_report.json`
- `audit.log`
- `report.html`
- evidence images under `evidence/`

`payload_sha256` is the SHA-256 of the canonical findings, coverage, and manifest. The HTML header embeds that digest. `file_sha256` is the SHA-256 of the HTML bytes. The CLI prints it, and the audit log stores it. The HTML file does not contain its own digest.

The audit log is JSON Lines. Each entry has `prev_hash` and `entry_hash`. The first `prev_hash` is 64 zeros. The writer fsyncs each append. `verify-log` detects an edit, a deletion, a reorder, and a truncation when the expected head from `run_manifest.json` is supplied. `LocalSha256Chain` does not sign entries. An entry that already carries a signature is refused by that verifier. If `cvassure.provenance.chain.SignedChain` imports, the pipeline uses it instead.

## Findings

JSON Schema 2020-12, `additionalProperties` false. Free-form values belong in `metadata`. The committed schema is `contracts/finding.schema.json`. Draft findings, which have no id yet, use `contracts/finding.draft.schema.json`.

Required fields include `schema_version` `1.0`, `id` matching `F-` and at least three digits, `asset`, `reason`, `evidence`, `severity`, `confidence`, `access_level`, `limitations`, `disposition`, and `linked_findings`. The pipeline assigns `id`. `asset` is `data`, `model`, `records`, `shift`, or `system`. `severity` and `confidence` are finite numbers from 0 to 1. `disposition` is `accept`, `review`, `quarantine`, or `rejected`. Evidence paths are relative to the run directory. An empty evidence list is allowed only for `asset` `system`.

A detector crash becomes one `system` finding, and the run continues with exit 3.

## Policy

`policies/default.yaml` decides disposition. Detectors may propose one. Policy overwrites it. An emitted finding that matches no rule is `review`. The default disposition cannot be `accept`.

Precedence is `rejected`, then `quarantine`, then `review`, then `accept`. The strongest match wins. A later rule wins a tie.

The file is loaded with `yaml.safe_load` and checked against `contracts/policy.schema.json`. There is no `eval` and no `exec`. An unknown field or operator is exit 2.

The numeric cut-offs in that file are uncalibrated starting values. Fit them on seeded data that includes negative controls before quoting them as measured thresholds. Do not put a contributor id, a class id, or a dataset name in a rule.

Current starting rules:

- Data with severity at least 0.8 and confidence at least 0.6 is quarantined at source scope.
- A model finding with severity at least 0.5 is review. A link does not quarantine the model.
- A records finding tagged `verification_failed` is rejected.
- A shift finding tagged `manipulation` is quarantined at batch scope.

## Linking

The linker reads `link_hints` only. It does not read a ground-truth attack manifest.

The score uses a class gate, then the components that both sides actually provide. Identity, from `patch_id`, has weight 0.5. Overlap, from IoU, has weight 0.2. Pattern, from normalised cross-correlation, has weight 0.3. Weights are renormalised over the components that exist. `tau_link` in `configs/demo.yaml` starts at 0.50 and is uncalibrated. A link can raise model severity with a noisy-OR. The linker does not change disposition.

Evidence paths that are absolute, contain `..`, or resolve outside the run directory are ignored.

## Coverage

Status is derived from a results CSV and `configs/coverage_rules.yaml`. A missing measurement is `Untested`, never `Supported`. A missing CSV is not an error. The CLI prints a warning, and non-declared classes stay `Untested`.

Three classes stay `Unsupported` by declaration:

- Adaptive attackers.
- Imperceptible clean-label perturbations.
- Hardware or compiler backdoors.

A measured row does not flip one of those three. Changing that list is a config change that must be documented.

## Adding a detector

Subclass `Detector`, set `id`, `asset`, `owner`, `version`, and `requires`, and implement `run`. Return a `DetectorResult`. Do not open sockets, do not write outside `ctx.out_dir`, and do not read a ground-truth attack manifest.

```python
from cvassure.core.detector import AuditContext, Detector, DetectorResult


class MyDetector(Detector):
    id = "data.my_check"
    asset = "data"
    owner = "data"
    version = "0.1.0"
    requires = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        return DetectorResult(summary="no signal")
```

Register it:

```toml
[project.entry-points."cvassure.detectors"]
my_check = "cvassure.data_integrity.my_check:MyDetector"
```

List the module in the run config so load order is explicit. A real module with the same id replaces the built-in stub. Two real modules with the same id are a config error. An import failure becomes a visible `system` finding.

## Layout

- `src/cvassure/core/` holds the schema, detector contract, registry, pipeline, CLI, policy, audit log, linking, and coverage.
- `src/cvassure/data_integrity/` holds training-data checks.
- `src/cvassure/model_integrity/` holds the model wrapper. The shipped `load_model` records a real SHA-256 of the file and does not open an ONNX session or a TorchScript module. `is_stub` is true.
- `src/cvassure/provenance/` is where a signed chain and `render_report` plug in.
- `src/cvassure/shift/` is where shift checks and `build_demo_scenario` plug in.
- `contracts/` holds the JSON Schemas the code loads.
- `policies/default.yaml` is the default policy.
- `configs/` holds the demo run config and the coverage rules.
- `scripts/make_offline_bundle.py` builds a wheelhouse.
- `scripts/nightly_demo.py` regenerates seed 42 and audits it.
- `scripts/smoke_demo.py` runs the same path and prints the CLI output.
- `tests/` holds unit and integration tests. `tests/fixtures/synthetic_scenario.py` builds a small synthetic dataset, unsigned JSONL records, and a tiny ONNX graph. That graph is not a trained or backdoored model. Contributor ids in that fixture are fixture values. Policy, the linker, and core logic do not hard-code them.

## Offline install

On a connected machine:

```bash
python scripts/make_offline_bundle.py
```

On the air-gapped machine:

```bash
pip install --no-index --find-links wheelhouse cvassure
```

`wheelhouse/` is gitignored.

## Development

```bash
pytest
ruff check .
ruff format --check .
pytest --disable-socket
```

CI runs Ubuntu and Windows on Python 3.11. The nightly workflow runs `scripts/nightly_demo.py`. It does not pass `--strict` while stubs are still registered.

Core dependencies are pydantic, PyYAML, jsonschema, typer, rich, and numpy. Matplotlib and Pillow are not core imports. IoU and normalised cross-correlation use NumPy.

## What is not in this tree

Signed audit-log entries, a Merkle tree, and a replacement HTML dashboard. Provide `cvassure.provenance.chain.SignedChain` and `cvassure.provenance.render_report` to take those over. Until then the local SHA-256 chain and the built-in HTML report are what a run writes.

Red-team mode and signed dataset or model cards are not implemented.

Coverage percentages are not invented. Without a results CSV, classes other than the three declared unsupported rows are `Untested`.

## Licence

MIT. See `LICENSE`.
