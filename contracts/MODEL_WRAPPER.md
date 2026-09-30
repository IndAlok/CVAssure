# MODEL_WRAPPER — access tier and capabilities

**Owner:** Person 3. **Status:** STRAWMAN, day 1. Person 1 wrote it, **Person 3 owns the
loader and the wrapper.** Person 1 only reads the first three members and uses them to decide
which detectors may run.

---

## 1. The wrapper

One class. It loads a model file and reports **honestly** what it can do with it.

```python
class CvModelWrapper:
    def __init__(self, model_path: Path, *, access: AccessTier) -> None: ...
    def declare_access_tier(self) -> AccessTier: ...  # white-box | gray-box | black-box
    def capabilities(self) -> frozenset[Capability]: ...  # {"weights", "gradients", ...}
    def weight_digest(self) -> str: ...  # sha256 hex of the model file
    def predict(self, batch) -> Predictions: ...
    def features(self, batch) -> Features: ...
    def gradients(self, batch) -> Gradients: ...
```

`AccessTier` and `Capability` are imported from `cvassure.core.detector`. Do not redeclare
them.

---

## 2. The access tier, and why it decides the run

| tier | you have | detectors allowed |
|---|---|---|
| `white-box` | weights, full graph, gradients | everything |
| `gray-box` | weights, forward pass, activations | activation clustering, spectral signatures, fingerprinting, weight digest |
| `black-box` | query interface only | behavioural fingerprinting, trigger sweep by query |
| `not-applicable` | no model in this run | data, records and shift detectors only |

`--access` on the CLI sets the **declared** tier. If the file does not actually support the
declared tier, the wrapper must say so at construction and the pipeline records the real tier.
Declaring white-box on an ONNX file you can only query is how the demo loses its credibility.

`capabilities()` is the machine-readable form and is what the pipeline checks against each
detector's `requires`. The two must agree; if they disagree, the wrapper is wrong.

**`requires` is a declared dependency, not a request.** A detector declaring
`requires={"gradients"}` on a gray-box model is skipped before `run` is called, with
`skipped_access_tier` recorded and a coverage row showing the assessment was unavailable. That
is PS §2.2.6 working: *"methods that require white-box access must fall back gracefully or
clearly report that the relevant assessment is unavailable."*

---

## 3. Missing capability returns a typed `Unavailable`

**Not an exception. Not a `None`. Not a plausible-looking zero.**

```python
@dataclass(frozen=True)
class Unavailable:
    reason: str  # "model is black-box; no gradients without weights"

    def __bool__(self) -> bool:
        return False
```

```python
g = wrapper.gradients(batch)
if not g:  # correct
    res.status = "skipped"
    res.skipped_reason = g.reason
    return res

np.asarray(g)  # wrong: crashes deep inside a detector
```

Returning a zero-filled array for unavailable gradients is the single worst thing you can do
here. It produces a real-looking trigger score of exactly nothing, which becomes a "clean"
result. Fail loudly, in a typed way, and let the pipeline record the skip.

---

## 4. Safe loaders

| format | how |
|---|---|
| ONNX | `onnxruntime` (import inside your module, never in core) |
| TorchScript | `torch.jit.load(path, map_location="cpu")` — a scripted archive, no pickle |
| PyTorch checkpoint | `torch.load(path, map_location="cpu", weights_only=True)` |
| anything else | raise at construction, do not guess |

**`weights_only=True` is not optional.** A `.pt` file is a pickle; loading one without that
flag executes whatever is in it. The whole product is an integrity tool. It cannot be the thing
that executes an attacker's payload.

The baseline assessment does **not** retrain the subject model (PS §2.2.6). If your detector
needs gradients for mask reconstruction, that is inference-time optimisation of a mask, not
training, and say so in `limitations`. Optional remediation may retrain; we do not do it.

---

## 5. `weight_digest()`

sha256 hex of the model file bytes. It goes into `run_manifest.json`, into every records
Finding's `config_hash`/`model_digest` comparison, and into the `fingerprint_mismatch` and
`weight_digest_mismatch` decisions. It must be the **file** digest, deterministic across
machines, and computed once at construction.

If you serialise the model to compute a structural digest instead, name it differently
(`structural_digest`) and keep `weight_digest()` as the file hash. Two different meanings
under one name is how a substitution check silently passes.

---

## 6. Your detectors

Register under your own ids (`model.trigger_sweep`, `model.fingerprint`, …),
`asset = "model"`, `owner = "P3"`, and declare `requires` truthfully.

**Emit `link_hints` on every trigger finding** — this is the demo's LINK line:

```json
"link_hints": {
  "target_class": 0,
  "trigger": { "kind": "reconstructed", "mask_path": "evidence/model_mask.png" },
  "location_bbox": [0.12, 0.11, 0.28, 0.29],
  "patch_template_path": "evidence/model_pattern.png"
}
```

Rules that will bite you if you miss them:

- **`kind: "reconstructed"` must not carry a `patch_id`.** The schema rejects it. Carrying one
  would fake an identity match you never measured. If you sweep a *known library patch*, use
  `kind: "patch_library"` with the real `patch_id`.
- **Bboxes are normalised 0–1, origin top-left.** `[x, y, w, h]`.
- **Emit only the evidence you have.** A black-box sweep has `patch_id` and class and nothing
  else. Emit that. The linker will link on identity alone and will note in `limitations` that
  pattern similarity was unavailable. Inventing a bbox to "help" the linker is how a false
  link gets into a demo.
- `limitations` names the method (Neural Cleanse, Fine-Pruning, …) and says what was not done.

Do not set `escalation` or `policy` — the linker and the policy engine own those.

---

## 7. The demo model (end of week 1)

Needed for the LINK line. `build_demo_scenario(seed=42)` must produce a model whose trigger is
the **same patch** as the data patch, so the linker has something real to match.

Nudge in standup until it lands. Until then the linker runs on synthetic unit tests only and
the demo has no LINK line, which is a correct but much weaker demo.

---

## 8. Acknowledgement

Tagging `contracts-v1` confirms the wrapper surface and the `Unavailable` convention.

- [ ] **P3** — wrapper surface, tiers, `Unavailable`, safe loaders. **PENDING day 1**
- [ ] **P1** — `declare_access_tier` + `capabilities` + `weight_digest` are all core reads.
      Acknowledged
- [ ] **P5** — backdoored and substituted model files for the scenario. **PENDING**
