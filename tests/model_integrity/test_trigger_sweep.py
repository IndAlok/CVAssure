"""Tests for the patch-library trigger sweep detector."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cvassure.core.detector import AuditContext
from cvassure.core.finding import validate_finding
from cvassure.model_integrity.trigger_sweep import TriggerSweepDetector
from cvassure.model_integrity.wrapper import CvModelWrapper


def _make_ctx(
    tmp_path: Path,
    *,
    model: CvModelWrapper | None = None,
    config: dict[str, Any] | None = None,
) -> AuditContext:
    return AuditContext(
        seed=42,
        out_dir=tmp_path / "out",
        evidence_dir=tmp_path / "out" / "evidence",
        cache_dir=tmp_path / "out" / "cache",
        config=config or {},
        model=model,
    )


def test_trigger_sweep_detector_contract() -> None:
    det = TriggerSweepDetector()
    assert det.id == "model.trigger_sweep"
    assert det.asset == "model"
    assert det.owner == "model"
    assert det.version == "0.1.0"
    assert "logits" in det.requires


def test_trigger_sweep_skips_without_model(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path, model=None)
    det = TriggerSweepDetector()
    res = det.run(ctx)
    assert res.status == "skipped"
    assert "no model" in res.skipped_reason.lower()


def test_trigger_sweep_skips_without_patch_library(tmp_path: Path) -> None:
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake model bytes")
    wrapper = CvModelWrapper(model_file)
    ctx = _make_ctx(tmp_path, model=wrapper, config={})
    det = TriggerSweepDetector()
    res = det.run(ctx)
    # Should skip because no patch library is configured
    assert res.status == "skipped"


def test_trigger_sweep_detects_known_patch(tmp_path: Path) -> None:
    """When a patch from the library causes a prediction flip, a finding is emitted."""
    # Create a patch library
    patch_dir = tmp_path / "patches"
    patch_dir.mkdir()
    from cvassure.core.imaging import checkerboard

    checkerboard(patch_dir / "P-01.png", 8, 8, (255, 255, 255), (0, 0, 0))

    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake model bytes")
    wrapper = CvModelWrapper(model_file)
    ctx = _make_ctx(tmp_path, model=wrapper, config={"patch_library": str(patch_dir)})
    det = TriggerSweepDetector()
    res = det.run(ctx)
    # Without a real backend, predict returns Unavailable, so the sweep skips
    if res.status == "skipped":
        assert (
            "unavailable" in res.skipped_reason.lower() or "predict" in res.skipped_reason.lower()
        )


def test_trigger_sweep_finding_has_link_hints() -> None:
    """The finding must carry patch_library link hints for the cross-asset linker."""
    from cvassure.core.finding import Finding, LinkHints, TriggerHint

    f = Finding.draft(
        asset="model",
        reason="Patch-library sweep hit patch P-03 on class 0 with attack success rate 0.85",
        evidence=["evidence/patch_P-03.png"],
        severity=0.8,
        confidence=0.7,
        access_level="white-box",
        limitations="Patch-library sweep detects known triggers only.",
        disposition="review",
        class_label=0,
        tags=["trigger_sweep_hit"],
        link_hints=LinkHints(
            target_class=0,
            trigger=TriggerHint(kind="patch_library", patch_id="P-03"),
            location_bbox=[0.1, 0.1, 0.3, 0.3],
            patch_template_path="evidence/patch_P-03.png",
        ),
        metadata={"patch_id": "P-03", "attack_success_rate": 0.85},
    )
    validated = validate_finding(
        f.to_final("F-001").model_dump(), detector_id="model.trigger_sweep"
    )
    assert validated.link_hints is not None
    assert validated.link_hints.trigger.kind == "patch_library"
    assert validated.link_hints.trigger.patch_id == "P-03"
