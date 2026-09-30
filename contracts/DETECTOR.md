# The Detector interface

**Owner:** Person 1. **Status:** frozen for `contracts-v1`.

A detector is a class. Four class attributes, one method. It returns Findings. If your real
detector is written against this interface unchanged, the contract held.

```python
class Detector(ABC):
    id: ClassVar[str]  # "data.patch_trigger"
    asset: ClassVar[str]  # data | model | records | shift
    owner: ClassVar[str]  # "P2" | "P3" | "P4" | "P5" | "P1"
    version: ClassVar[str]  # "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()  # {"weights", "gradients", ...}

    def configure(self, cfg: Mapping[str, Any]) -> None: ...
    def run(self, ctx: AuditContext) -> DetectorResult: ...
```

---

## 1. The five class attributes

| attribute | rule | consequence if wrong |
|---|---|---|
| `id` | dotted, stable, unique across the registry. Never reused after a rename | a real module and its stub must use the **same** id, so the registry can prefer the real one |
| `asset` | one of `data`, `model`, `records`, `shift` | wrong stage ordering on the CLI |
| `owner` | `P1`…`P5` | audit log credits the wrong person |
| `version` | bump on any behaviour change | the audit log cannot tell two runs apart |
| `requires` | `frozenset` of wrapper capabilities, empty if you work on any tier | a white-box method silently runs on a black-box model |

`requires` is not documentation. It is how the pipeline decides to **skip** you honestly
instead of letting you crash. Declare it truthfully and a black-box run produces a coverage
row that says "this assessment was unavailable", which is a correct and defensible result.

---

## 2. `AuditContext` — read-only, and no ground truth

Frozen dataclass. Every field you may read:

| field | what it is |
|---|---|
| `dataset` | `Dataset` handle, or `None`. `dataset.samples` is a tuple of `Sample(sample_id, path, class_id, source_id, batch_id)` |
| `model` | `ModelWrapper` from P3, or `None`. Has `declare_access_tier()`, `capabilities()`, `weight_digest()` |
| `records_path` | path to the inference records, or `None` |
| `pubkey_path` | Ed25519 public key path once P4 lands, or `None` |
| `config` | loaded config mapping, read-only |
| `seed` | the run seed. **Use it.** Every random choice must derive from it |
| `out_dir`, `evidence_dir`, `cache_dir` | where you may write, and nowhere else |
| `logger` | stdlib logger |
| `audit` | append-only handle for structured events, or `None` |
| `prior_findings` | findings from earlier stages, read-only tuple |

**There is no attribute for Person 5's ground-truth manifest, and that is deliberate.** If your
method needs to know which samples were poisoned in order to work, it is an evaluation script,
not a detector — put it under `scripts/`. A detector that reads ground truth produces a
detection rate of 1.0 and tells nobody anything.

Write with `ctx.stage_out("evidence", "foo.png")` or under `ctx.evidence_dir`. Nothing else.

---

## 3. `DetectorResult`

```python
@dataclass
class DetectorResult:
    status: Literal["ok", "skipped", "error"] = "ok"
    findings: list[Finding] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    summary: str = ""  # the right-hand text on the CLI line
    artifacts: list[str] = field(default_factory=list)  # relative to out_dir
    limitations: list[str] = field(default_factory=list)  # folded into coverage
    skipped_reason: str | None = None
    runtime_s: float | None = None  # measured by the pipeline, not by you
```

`summary` is one line, no newlines, roughly 40 characters. It is what a judge reads first, so
make it the number: `"0.71 sweep hit on class 0"`, not `"found something interesting"`.

`metrics` keys are yours alone. They land in the run manifest for your stage.

**Return Findings. Never ad-hoc dicts.** A dict is how a finding silently loses its
`limitations` field, and `limitations` is the one field a judge will read.

---

## 4. The copy-paste stub

About 30 lines. This is the whole contract.

```python
"""data.patch_trigger — P2's patched-sample detector."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Mapping

from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.finding import Finding, LinkHints, TriggerHint


class PatchTriggerDetector(Detector):
    id: ClassVar[str] = "data.patch_trigger"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "P2"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()  # data-side, no model access

    def configure(self, cfg: Mapping[str, Any]) -> None:
        self.patch_library = Path(cfg["patch_library"])  # per-detector config lives here

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.dataset is None:
            res.status = "skipped"
            res.skipped_reason = "no dataset in this run"
            return res

        hits = []  # your real logic here
        for sample in ctx.dataset.samples:
            if self._carries_patch(sample.path):
                hits.append(sample)

        if not hits:
            res.summary = "0 patched samples"
            return res

        top = Finding.draft(
            asset="data",
            reason=f"patch trigger matched {len(hits)} samples from one contributor",
            evidence=[f"evidence/{self.id.replace('.', '_')}.png"],
            severity=0.9,  # impact if true
            confidence=0.85,  # belief it is true
            access_level="not-applicable",
            limitations="Patch library covers 1 known trigger; novel triggers are missed.",
            disposition="review",  # policy overwrites this
            source_id=hits[0].source_id,
            class_label=hits[0].class_id,
            sample_ids=[s.sample_id for s in hits][:50],
            sample_count=len(hits),
            tags=["patch_trigger"],
            link_hints=LinkHints(
                target_class=hits[0].class_id,
                source_id=hits[0].source_id,
                trigger=TriggerHint(kind="patch_library", patch_id="P-03"),
                location_bbox=[0.1, 0.1, 0.3, 0.3],  # normalised, top-left origin
                patch_template_path="evidence/patch_P-03.png",
            ),
            metadata={"n_checked": len(ctx.dataset.samples)},
        )
        res.findings.append(top)
        res.summary = f"{len(hits)} patched samples, top source {hits[0].source_id}"
        return res
```

Note what the stub does **not** do: no `id`, no `detector`, no `escalation`, no `policy`. The
pipeline fills those.

---

## 5. Registering it

Entry point, in your package's `pyproject.toml`:

```toml
[project.entry-points."cvassure.detectors"]
patch_trigger = "cvassure.data_integrity.patch_trigger:PatchTriggerDetector"
```

Plus the module in `configs/demo.yaml` so the load order is explicit and reproducible. The
registry loads entry points first, then the configured module list, then falls back to the
built-in stub when the real module is missing. A real module always wins over a stub with the
same id — that is how your detector replaces the day-2 stub without anyone editing core.

---

## 6. Two rules the pipeline enforces for you

**Crash isolation.** If your `run` raises, the pipeline catches it, writes **one**
`asset=system` Finding naming you, marks you `error`, and continues with the other detectors.
The process does not die. The run ends with exit code 3 and your name in the manifest. You do
not need a defensive `try` block; you do need your `limitations` on that system Finding to be
honest about what did not run.

**Access skip.** If `requires` is not a subset of `model.capabilities()`, the pipeline never
calls `run`. You get `status="skipped"`, a reason like
`requires white-box; model is black-box`, and a coverage row showing the assessment was
unavailable. Never write code that pretends a method ran when the tier forbade it — that is
the single easiest way to lose the demo on a judge's "how do you know?" question.

---

## 7. Determinism

Detectors must be deterministic given `ctx.seed`. Two `--reproducible` runs write
byte-identical `findings.json`. That means:

- seed every RNG from `ctx.seed`, never from the global `random` or `np.random`
- do not put wall-clock time, a temp path, or a PID in `reason`, `metadata` or `summary`
- sort anything you iterate over before it reaches a Finding, unless the order is meaningful
  and stable (severity descending, sample order)
- do not write a duration into `metadata`; the pipeline times you

---

## 8. Security rules, enforced and not

These are checked, not requested:

- **No sockets.** A test runs the stub audit with `socket.socket` disabled. A detector that
  phones home is a bug.
- **No `pickle` of untrusted checkpoints.** That is P3's loader rule and it applies to you if
  you load a model. `torch.load(weights_only=True)` and friends.
- **Evidence paths stay under `out/evidence/`.** Absolute, drive-lettered, backslash and `..`
  paths are rejected by the schema.
- **`sample_ids` caps at 50.** A flood of ids is a denial of service on the report.
- **Write only under `out_dir`.** Anything else is a bug we find in review.
