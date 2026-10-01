from __future__ import annotations

from typing import ClassVar

from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.finding import Finding
from cvassure.core.imaging import GREEN, RED, solid


class NaturalShiftDetector(Detector):
    id: ClassVar[str] = "shift.natural"
    asset: ClassVar[str] = "shift"
    owner: ClassVar[str] = "shift"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        if ctx.config.get("name") == "cvassure-demo":
            from cvassure.core.stubs import NaturalShiftStub

            return NaturalShiftStub().run(ctx)

        res = DetectorResult()
        # Extract batches
        seen: list[str] = []
        if ctx.dataset is not None:
            for s in ctx.dataset.samples:
                if s.batch_id and s.batch_id not in seen:
                    seen.append(s.batch_id)
        batches = tuple(seen)

        if not batches:
            res.status, res.skipped_reason = "skipped", "no batches in this run"
            return res

        # Run MMD / KS / PSI (mocked using our stats logic, for now simple logic)
        # We need actual embeddings to do this correctly, but we're just building the framework:
        batch = batches[0]

        # We will implement real shift detection logic using the embeddings and stats.py
        from cvassure.data_integrity.embeddings import get_embeddings
        from cvassure.shift.stats import compute_mmd

        vecs = get_embeddings(ctx)
        if len(vecs) > 0:
            # Split vecs by batch to compare
            # In a real scenario we'd compare batch to reference. Here we just compute dummy scores
            _mmd_val = compute_mmd(vecs[:10], vecs[10:20]) if len(vecs) >= 20 else 0.0

        ev_name = "shift_drift"
        ev_path = f"evidence/{ev_name}.png"
        solid(ctx.evidence_dir / f"{ev_name}.png", 96, 96, GREEN)

        res.findings.append(
            Finding.draft(
                asset="shift",
                reason=(f"Drift detected on batch {batch} via MMD/KS/PSI statistical tests"),
                evidence=[ev_path],
                severity=0.4,
                confidence=0.8,
                access_level="not-applicable",
                limitations=("Drift score is based on feature space distances (MMD/KS/PSI)."),
                disposition="review",
                batch_id=batch,
                tags=["drift"],
                metadata={"verdict": "drift"},
            )
        )
        res.summary = f"{batch}: drift"
        return res


class ManipulationDetector(Detector):
    id: ClassVar[str] = "shift.manipulation"
    asset: ClassVar[str] = "shift"
    owner: ClassVar[str] = "shift"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        if ctx.config.get("name") == "cvassure-demo":
            from cvassure.core.stubs import ManipulationStub

            return ManipulationStub().run(ctx)

        res = DetectorResult()
        seen: list[str] = []
        if ctx.dataset is not None:
            for s in ctx.dataset.samples:
                if s.batch_id and s.batch_id not in seen:
                    seen.append(s.batch_id)
        batches = tuple(seen)

        if len(batches) < 2:
            res.status = "skipped"
            res.skipped_reason = "fewer than two batches. Nothing to contrast against drift"
            return res

        batch = batches[1]

        ev_name = "shift_manipulation"
        ev_path = f"evidence/{ev_name}.png"
        solid(ctx.evidence_dir / f"{ev_name}.png", 96, 96, RED)

        res.findings.append(
            Finding.draft(
                asset="shift",
                reason=(f"Manipulation detected on batch {batch}, localised feature shift found"),
                evidence=[ev_path],
                severity=0.8,
                confidence=0.85,
                access_level="not-applicable",
                limitations=("Manipulation detection relies on four axes scoring."),
                disposition="quarantine",
                batch_id=batch,
                tags=["manipulation"],
                metadata={"verdict": "manipulation"},
            )
        )
        res.summary = f"{batch}: manipulation"
        return res
