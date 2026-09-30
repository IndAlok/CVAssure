# Handover

Person 1 owns the spine: schema, detector contract, CLI, plugin loader, YAML policy, audit log, coverage statement, and cross-asset linking. Persons 2-5 own the detectors. This file is how to run what exists and what is still blocked.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
python scripts/nightly_demo.py --out out
```

`python scripts/nightly_demo.py` builds the synthetic scenario under `.demo_scratch/` and audits it. `cvassure demo` exits 2 with `BLOCKED-ON: P5` until `cvassure.shift.scenario.build_demo_scenario` exists. `cvassure audit --strict` exits 5 while any stub detector runs. A slide screenshot needs exit 0 and no `STUB` line.

## Regenerate images

```bash
python scripts/nightly_demo.py --out out
pip install matplotlib pillow
python scripts/make_images.py --out out --images docs/images
```

`docs/diagrams/architecture.dot` is the diagram source. The PNG files in `docs/images/` are from a stub run until the strict audit exits 0. Captions sit beside each PNG. `docs/images/MANIFEST.txt` maps file, slide, and caption.

## What is finished

- Finding schema, draft schema, and both validators.
- Detector contract, registry, stubs, CLI, pipeline, policy, hash-chained audit log, linker, coverage generator, fallback HTML report.
- Contracts for the other four owners, still waiting on acknowledgement.
- CI on Ubuntu and Windows, Python 3.11, including integration tests.

## What is blocked

- Real detectors, embeddings, backdoored model, Ed25519 chain, HTML dashboard, and `results_table.csv`. Owners: P2, P3, P4, P5.
- Coverage rows stay `Untested` until that CSV exists. Declared unsupported rows stay unsupported.
- Link threshold `tau_link` is 0.50 and marked `UNCALIBRATED`.
- GitHub handles in `CODEOWNERS` are still `P2` through `P5`.
- Daily call time in `docs/p1/DAY1_MESSAGE.md` is still `[[FILL]]`.

## Limits

The audit never reads Person 5's ground-truth manifest. A missing model wrapper skips any detector that declares `requires`. Evidence paths that leave `out/` are ignored. The report uses two hashes: `payload_sha256` inside the HTML, `file_sha256` of the HTML bytes. Stretch work (red-team mode, signed cards) is not started.
