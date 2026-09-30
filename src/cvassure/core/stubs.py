"""Built-in detector stubs.

Each stub uses the id a real detector will use. The registry prefers a real
module with the same id.

A stub sets `stub` true, starts `reason` with `[STUB]`, and makes
`cvassure audit --strict` exit 5.

The source id, class, and patch id below are fixture values. They are not
measurements, and they are not read by policy or the linker as constants.
"""

from __future__ import annotations

from typing import Any, ClassVar

from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.finding import Finding, LinkHints, TriggerHint
from cvassure.core.imaging import BLUE, GREEN, NAVY, RED, checkerboard, solid

STUB_REASON_PREFIX = "[STUB]"

# Fixture values for the built-in stubs. Policy and the linker do not import these.
DEMO_SOURCE = "C-07"
DEMO_CLASS = 0
DEMO_PATCH_ID = "P-03"


class _StubBase(Detector):
    """Shared stub plumbing. Not a detector itself. Never registered."""

    def _evidence(self, ctx: AuditContext, name: str, color: tuple[int, int, int]) -> str:
        rel = f"evidence/{name}.png"
        solid(ctx.evidence_dir / f"{name}.png", 96, 96, color)
        return rel

    @staticmethod
    def _finalise(res: DetectorResult, ctx: AuditContext) -> DetectorResult:
        for f in res.findings:
            f.stub = True
            if not f.reason.startswith(STUB_REASON_PREFIX):
                f.reason = f"{STUB_REASON_PREFIX} {f.reason}"[:300]
            f.limitations = (f"[STUB] Not a measurement. {f.limitations}")[:300]
        return res

    @staticmethod
    def _batches(ctx: AuditContext) -> tuple[str, ...]:
        """Batch ids from the dataset, in first-seen order. Never a literal.

        The shift stage names two batches to show a drift verdict and a
        manipulation verdict side by side. Which two is a property of the input,
        so the stub reads them from the data like a real detector would.
        """
        seen: list[str] = []
        if ctx.dataset is not None:
            for s in ctx.dataset.samples:
                if s.batch_id and s.batch_id not in seen:
                    seen.append(s.batch_id)
        return tuple(seen)


class PatchTriggerStub(_StubBase):
    id: ClassVar[str] = "data.patch_trigger"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "data"
    version: ClassVar[str] = "0.1.0-stub"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.dataset is None:
            res.status, res.skipped_reason = "skipped", "no dataset in this run"
            return res
        n = len(ctx.dataset.samples)
        res.findings.append(
            Finding.draft(
                asset="data",
                reason=(
                    f"[STUB] fixture patch trigger, source {DEMO_SOURCE}, "
                    f"1 of {n} samples carries patch {DEMO_PATCH_ID}"
                ),
                evidence=[self._evidence(ctx, "stub_data_patch", BLUE)],
                severity=0.9,
                confidence=0.6,
                access_level="not-applicable",
                limitations=(
                    "STUB: built-in fixture. This number is not a measurement. "
                    "value chosen to exercise the pipeline, not a detection result."
                ),
                disposition="review",
                source_id=DEMO_SOURCE,
                class_label=DEMO_CLASS,
                sample_ids=[s.sample_id for s in ctx.dataset.samples[:3]],
                sample_count=1,
                tags=["patch_trigger"],
                link_hints=LinkHints(
                    target_class=DEMO_CLASS,
                    source_id=DEMO_SOURCE,
                    trigger=TriggerHint(kind="patch_library", patch_id=DEMO_PATCH_ID),
                    location_bbox=[0.1, 0.1, 0.3, 0.3],
                    patch_template_path="evidence/stub_patch_template.png",
                ),
                metadata={"stub": True, "fixture": True},
            )
        )
        # Textured, not flat: two flat images correlate 0/0, so a solid template
        # would silently disable the `pattern` component of the linker in every
        # fixture run. See `imaging.checkerboard`.
        checkerboard(ctx.evidence_dir / "stub_patch_template.png", 96, 96, BLUE, (255, 255, 255))
        res.summary = f"1 fixture patch finding, top source {DEMO_SOURCE}"
        return self._finalise(res, ctx)


class NearDuplicateStub(_StubBase):
    id: ClassVar[str] = "data.near_duplicate"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "data"
    version: ClassVar[str] = "0.1.0-stub"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult(
            status="skipped",
            skipped_reason="STUB: built-in near-duplicate check is not a measurement",
        )
        res.summary = "skipped (built-in stub)"
        return res


class TriggerSweepStub(_StubBase):
    id: ClassVar[str] = "model.trigger_sweep"
    asset: ClassVar[str] = "model"
    owner: ClassVar[str] = "model"
    version: ClassVar[str] = "0.1.0-stub"
    requires: ClassVar[frozenset[str]] = frozenset({"weights"})

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.model is None:
            res.status, res.skipped_reason = "skipped", "no model in this run"
            return res
        tier = ctx.model.declare_access_tier()
        # A sweep of a KNOWN library patch carries the patch id, so the linker
        # links on identity and needs no mask. Declaring it `reconstructed` would
        # claim a mask reconstruction this stub never performed, and would also
        # carry no identity component at all.
        res.findings.append(
            Finding.draft(
                asset="model",
                reason=(
                    f"[STUB] fixture white-box library-patch sweep hit patch "
                    f"{DEMO_PATCH_ID} on class {DEMO_CLASS}"
                ),
                evidence=[self._evidence(ctx, "stub_model_sweep", NAVY)],
                severity=0.7,
                confidence=0.6,
                access_level=tier if tier != "not-applicable" else "white-box",
                limitations=(
                    "STUB: built-in fixture score. No "
                    "mask reconstruction was performed."
                ),
                disposition="review",
                class_label=DEMO_CLASS,
                sample_count=1,
                tags=["trigger_sweep_hit"],
                link_hints=LinkHints(
                    target_class=DEMO_CLASS,
                    trigger=TriggerHint(kind="patch_library", patch_id=DEMO_PATCH_ID),
                    location_bbox=[0.12, 0.11, 0.28, 0.29],
                    # A sweep of a known library entry has that entry's template,
                    # so the pattern component is computable. This is the same
                    # fixture image the data stub emits, which is what makes the
                    # NCC component non-zero in a fixture run.
                    patch_template_path="evidence/stub_patch_template.png",
                ),
                metadata={"stub": True, "fixture": True, "sweep_r": 0.71},
            )
        )
        solid(ctx.evidence_dir / "stub_model_sweep.png", 96, 96, NAVY)
        res.summary = f"fixture sweep hit on class {DEMO_CLASS}, patch {DEMO_PATCH_ID}"
        return self._finalise(res, ctx)


class RecordVerifyStub(_StubBase):
    id: ClassVar[str] = "records.verify"
    asset: ClassVar[str] = "records"
    owner: ClassVar[str] = "records"
    version: ClassVar[str] = "0.1.0-stub"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.records_path is None or not ctx.records_path.is_file():
            res.status, res.skipped_reason = "skipped", "no records in this run"
            return res

        total = _count_records(ctx.records_path)
        for rec_id, kind in (("rec-0007", "edited"), ("rec-0012", "replayed")):
            res.findings.append(
                Finding.draft(
                    asset="records",
                    reason=(
                        f"[STUB] fixture record {rec_id} {kind}, "
                        "signature and sequence checks not performed"
                    ),
                    evidence=[self._evidence(ctx, f"stub_record_{rec_id}", RED)],
                    severity=0.7 if kind == "edited" else 0.65,
                    confidence=0.5,
                    access_level="not-applicable",
                    limitations=(
                        "STUB: built-in record check. Nothing was actually "
                        "verified. These records are presumed-bad fixture rows."
                    ),
                    disposition="review",
                    sample_ids=[rec_id],
                    sample_count=1,
                    tags=["verification_failed", "replay"]
                    if kind == "replayed"
                    else ["verification_failed"],
                    metadata={"stub": True, "fixture": True, "modification": kind},
                )
            )
        res.summary = f"{total} records, 2 fixture REJECTED (1 edited, 1 replayed)"
        return self._finalise(res, ctx)


def _count_records(path: Any) -> int:
    """Read the record count from JSONL. Counts only. The stub verifies nothing."""
    total = 0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                total += 1
    except OSError:
        return 0
    return total


class NaturalShiftStub(_StubBase):
    """Probable operational drift on one batch. Batch ids come from the data."""

    id: ClassVar[str] = "shift.natural"
    asset: ClassVar[str] = "shift"
    owner: ClassVar[str] = "shift"
    version: ClassVar[str] = "0.1.0-stub"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        batches = self._batches(ctx)
        if not batches:
            res.status, res.skipped_reason = "skipped", "no batches in this run"
            return res
        batch = batches[0]
        res.findings.append(
            Finding.draft(
                asset="shift",
                reason=(f"[STUB] fixture drift on batch {batch}, distribution stats not computed"),
                evidence=[self._evidence(ctx, "stub_shift_drift", GREEN)],
                severity=0.3,
                confidence=0.5,
                access_level="not-applicable",
                limitations=(
                    "STUB: built-in shift check. No MMD, KS or PSI was "
                    "computed and no reference distribution was compared."
                ),
                disposition="review",
                batch_id=batch,
                tags=["drift"],
                metadata={"stub": True, "fixture": True, "verdict": "drift"},
            )
        )
        res.summary = f"{batch}: drift"
        return self._finalise(res, ctx)


class ManipulationStub(_StubBase):
    """Suspicious manipulation on a second batch, not a natural shift.

    The pair with `NaturalShiftStub` is the point: two batches, two different
    verdicts, one row each on the demo line. Same fixture caveats.
    """

    id: ClassVar[str] = "shift.manipulation"
    asset: ClassVar[str] = "shift"
    owner: ClassVar[str] = "shift"
    version: ClassVar[str] = "0.1.0-stub"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        batches = self._batches(ctx)
        if len(batches) < 2:
            res.status = "skipped"
            res.skipped_reason = "fewer than two batches. Nothing to contrast against drift"
            return res
        batch = batches[1]
        res.findings.append(
            Finding.draft(
                asset="shift",
                reason=(
                    f"[STUB] fixture manipulation on batch {batch}, "
                    "localised rather than global shift"
                ),
                evidence=[self._evidence(ctx, "stub_shift_manipulation", RED)],
                severity=0.75,
                confidence=0.5,
                access_level="not-applicable",
                limitations=(
                    "STUB: built-in shift check. Drift and manipulation "
                    "are not actually distinguished by any computed statistic here."
                ),
                disposition="review",
                batch_id=batch,
                tags=["manipulation"],
                metadata={"stub": True, "fixture": True, "verdict": "manipulation"},
            )
        )
        res.summary = f"{batch}: manipulation"
        return self._finalise(res, ctx)


#: Loaded by the registry after entry points and config modules. A real module
#: with the same id replaces its stub automatically.
STUB_MODULES: tuple[str, ...] = (
    "cvassure.core.stubs:PatchTriggerStub",
    "cvassure.core.stubs:NearDuplicateStub",
    "cvassure.core.stubs:TriggerSweepStub",
    "cvassure.core.stubs:RecordVerifyStub",
    "cvassure.core.stubs:NaturalShiftStub",
    "cvassure.core.stubs:ManipulationStub",
)
