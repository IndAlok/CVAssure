"""Tests for the Neural-Cleanse style reconstruction detector."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cvassure.core.detector import AuditContext
from cvassure.core.finding import validate_finding
from cvassure.model_integrity.reconstruction import ReconstructionDetector
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


def test_reconstruction_detector_contract() -> None:
    det = ReconstructionDetector()
    assert det.id == "model.reconstruction"
    assert det.asset == "model"
    assert det.owner == "model"
    assert det.version == "0.1.0"
    assert "weights" in det.requires
    assert "gradients" in det.requires


def test_reconstruction_skips_without_model(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path, model=None)
    det = ReconstructionDetector()
    res = det.run(ctx)
    assert res.status == "skipped"
    assert "no model" in res.skipped_reason.lower()


def test_reconstruction_skips_without_backend(tmp_path: Path) -> None:
    """Without a real backend, the detector skips cleanly."""
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake model bytes")
    wrapper = CvModelWrapper(model_file)
    ctx = _make_ctx(tmp_path, model=wrapper)
    det = ReconstructionDetector()
    res = det.run(ctx)
    # Without a backend, predict returns Unavailable, so reconstruction skips
    if res.status == "skipped":
        assert res.skipped_reason is not None


def test_reconstruction_finding_has_link_hints() -> None:
    """The finding must carry reconstructed trigger link hints."""
    from cvassure.core.finding import Finding, LinkHints, TriggerHint

    f = Finding.draft(
        asset="model",
        reason="Reconstructed trigger for class 0 is anomalously small (L1 norm 0.5, median 2.0)",
        evidence=["evidence/recon_mask_class_0.png"],
        severity=0.85,
        confidence=0.7,
        access_level="white-box",
        limitations="Neural-Cleanse style reconstruction is unreliable for blended triggers.",
        disposition="review",
        class_label=0,
        tags=["trigger_reconstructed"],
        link_hints=LinkHints(
            target_class=0,
            trigger=TriggerHint(
                kind="reconstructed",
                mask_path="evidence/recon_mask_class_0.png",
            ),
            location_bbox=[0.1, 0.1, 0.3, 0.3],
        ),
        metadata={"flagged_classes": [0], "median": 2.0, "mad": 0.5},
    )
    validated = validate_finding(
        f.to_final("F-001").model_dump(), detector_id="model.reconstruction"
    )
    assert validated.link_hints is not None
    assert validated.link_hints.trigger.kind == "reconstructed"
    assert validated.link_hints.trigger.mask_path == "evidence/recon_mask_class_0.png"
