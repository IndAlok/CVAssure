"""Detector interface tests (D3).

The interface has no logic, so these tests check the three things the pipeline
actually relies on: the contract check catches a broken detector, the context has
no attribute for ground truth, and the documented 30-line stub really works.
"""

from __future__ import annotations

import dataclasses
import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar

import pytest

from cvassure.core.detector import (
    AuditContext,
    Dataset,
    Detector,
    DetectorResult,
    Sample,
    interface_errors,
)
from cvassure.core.finding import Finding, LinkHints, TriggerHint


class Good(Detector):
    id: ClassVar[str] = "data.good"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "data"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        return DetectorResult(summary="nothing")


def test_a_conforming_detector_has_no_contract_errors() -> None:
    assert interface_errors(Good()) == []


@pytest.mark.parametrize(
    ("attr", "value", "needle"),
    [
        ("id", "", "id"),
        ("version", "", "version"),
        ("owner", "", "owner"),
        ("asset", "dataset", "asset"),
        ("asset", "system", "asset"),  # system is written by the pipeline, not a detector
        ("requires", frozenset, "requires"),
    ],
)
def test_contract_check_catches_a_broken_detector(attr, value, needle) -> None:
    broken = Good()
    setattr(broken, attr, value)
    problems = interface_errors(broken)
    assert any(needle in p for p in problems), f"{attr}={value!r} not caught: {problems}"


def test_detector_cannot_be_instantiated_without_run() -> None:
    class NoRun(Detector):
        id: ClassVar[str] = "x"
        asset: ClassVar[str] = "data"
        owner: ClassVar[str] = "core"
        version: ClassVar[str] = "0"

    with pytest.raises(TypeError):
        NoRun()  # type: ignore[abstract]


def test_audit_context_has_no_ground_truth_attribute() -> None:
    """The whole detection-rate argument depends on this being true."""
    fields = {f.name for f in dataclasses.fields(AuditContext)}
    for banned in ("manifest", "ground_truth", "truth", "manifest_path", "eval", "labels_truth"):
        assert banned not in fields, f"AuditContext must not expose {banned}"
    assert "audit" in fields and "prior_findings" in fields


def test_audit_context_is_frozen() -> None:
    ctx = AuditContext(
        seed=42, out_dir=Path("o"), evidence_dir=Path("o/e"), cache_dir=Path("o/c"), config={}
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.seed = 7  # type: ignore[misc]


def test_stage_out_stays_under_out_dir(tmp_path: Path) -> None:
    ctx = AuditContext(
        seed=1,
        out_dir=tmp_path,
        evidence_dir=tmp_path / "evidence",
        cache_dir=tmp_path / "cache",
        config={},
    )
    p = ctx.stage_out("evidence", "x.png")
    assert p.is_relative_to(tmp_path)
    assert p.parent.is_dir()


def test_dataset_helpers() -> None:
    s = [
        Sample("s1", Path("a.png"), 0, "C-07", "B-1"),
        Sample("s2", Path("b.png"), 0, "C-07", "B-1"),
        Sample("s3", Path("c.png"), 1, "C-01", "B-2"),
        Sample("s4", Path("d.png"), 1, None, "B-2"),
    ]
    ds = Dataset(root=Path("."), format="coco", samples=tuple(s))
    assert ds.sources() == ("C-01", "C-07")
    assert [x.sample_id for x in ds.by_source("C-07")] == ["s1", "s2"]


def test_result_defaults_are_inert() -> None:
    r = DetectorResult()
    assert (r.status, r.findings, r.metrics, r.summary) == ("ok", [], {}, "")
    assert r.skipped_reason is None and r.runtime_s is None


# A minimal detector, executed as written.


class PatchTriggerDetector(Detector):
    id: ClassVar[str] = "data.patch_trigger"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "data"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def configure(self, cfg: Mapping[str, Any]) -> None:
        self.patch_library = Path(cfg["patch_library"])

    def _carries_patch(self, path: Path) -> bool:
        return path.name.startswith("patched")

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.dataset is None:
            res.status = "skipped"
            res.skipped_reason = "no dataset in this run"
            return res

        hits = [s for s in ctx.dataset.samples if self._carries_patch(s.path)]
        if not hits:
            res.summary = "0 patched samples"
            return res

        res.findings.append(
            Finding.draft(
                asset="data",
                reason=f"patch trigger matched {len(hits)} samples from one contributor",
                evidence=[f"evidence/{self.id.replace('.', '_')}.png"],
                severity=0.9,
                confidence=0.85,
                access_level="not-applicable",
                limitations="Patch library covers 1 known trigger. Novel triggers are missed.",
                disposition="review",
                source_id=hits[0].source_id,
                class_label=hits[0].class_id,
                sample_ids=[s.sample_id for s in hits][:50],
                sample_count=len(hits),
                tags=["patch_trigger"],
                link_hints=LinkHints(
                    target_class=hits[0].class_id,
                    source_id=hits[0].source_id,
                    trigger=TriggerHint(kind="patch_library", patch_id="P-03"),
                    location_bbox=[0.1, 0.1, 0.3, 0.3],
                    patch_template_path="evidence/patch_P-03.png",
                ),
                metadata={"n_checked": len(ctx.dataset.samples)},
            )
        )
        res.summary = f"{len(hits)} patched samples, top source {hits[0].source_id}"
        return res


def test_documented_stub_runs_and_emits_a_valid_finding(tmp_path: Path) -> None:
    """If the doc's stub breaks, the contract is lying to four other people."""
    ds = Dataset(
        root=tmp_path,
        format="coco",
        samples=(
            Sample("s1", tmp_path / "patched_a.png", 0, "C-07", "B-1"),
            Sample("s2", tmp_path / "patched_b.png", 0, "C-07", "B-1"),
            Sample("s3", tmp_path / "clean_c.png", 1, "C-01", "B-2"),
        ),
    )
    det = PatchTriggerDetector()
    det.configure({"patch_library": tmp_path})
    ctx = AuditContext(
        seed=42,
        out_dir=tmp_path / "out",
        evidence_dir=tmp_path / "out/evidence",
        cache_dir=tmp_path / "out/cache",
        config={},
        dataset=ds,
    )
    res = det.run(ctx)

    assert res.status == "ok"
    assert res.summary == "2 patched samples, top source C-07"
    assert len(res.findings) == 1
    f = res.findings[0]
    assert f.id is None  # no id on a draft
    assert f.link_hints is not None and f.link_hints.trigger.patch_id == "P-03"
    assert f.to_final("F-001").to_final("F-001").id == "F-001"  # pipeline can finish it


def test_documented_stub_skips_cleanly_without_a_dataset(tmp_path: Path) -> None:
    ctx = AuditContext(
        seed=42, out_dir=tmp_path, evidence_dir=tmp_path / "e", cache_dir=tmp_path / "c", config={}
    )
    res = PatchTriggerDetector().run(ctx)
    assert res.status == "skipped"
    assert res.skipped_reason == "no dataset in this run"
    assert res.findings == []


def test_audit_context_signature_is_stable() -> None:
    """A contract change to AuditContext is a team event. Catch it here."""
    params = list(inspect.signature(AuditContext).parameters)
    assert params == [
        "seed",
        "out_dir",
        "evidence_dir",
        "cache_dir",
        "config",
        "dataset",
        "model",
        "records_path",
        "pubkey_path",
        "logger",
        "audit",
        "prior_findings",
    ]
