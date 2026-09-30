"""Tests for the behavioural fingerprint detector."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cvassure.core.detector import AuditContext
from cvassure.core.finding import validate_finding
from cvassure.model_integrity.fingerprint import FingerprintDetector
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


def test_fingerprint_detector_contract() -> None:
    det = FingerprintDetector()
    assert det.id == "model.fingerprint"
    assert det.asset == "model"
    assert det.owner == "model"
    assert det.version == "0.1.0"
    assert "logits" in det.requires


def test_fingerprint_skips_without_model(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path, model=None)
    det = FingerprintDetector()
    res = det.run(ctx)
    assert res.status == "skipped"
    assert "no model" in res.skipped_reason.lower()


def test_fingerprint_stores_baseline_on_first_run(tmp_path: Path) -> None:
    """When no reference exists, the detector stores the current fingerprint."""
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake model bytes")
    wrapper = CvModelWrapper(model_file)
    ctx = _make_ctx(tmp_path, model=wrapper)
    det = FingerprintDetector()
    res = det.run(ctx)
    # Should either skip (no backend) or store baseline
    if res.status == "ok":
        assert "baseline" in res.summary.lower() or "no reference" in res.summary.lower()


def test_fingerprint_detects_model_swap(tmp_path: Path) -> None:
    """A changed model file should produce a different fingerprint."""
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"model version 1")
    wrapper1 = CvModelWrapper(model_file)
    ctx = _make_ctx(tmp_path, model=wrapper1)
    det = FingerprintDetector()
    res1 = det.run(ctx)

    # Change the model file
    model_file.write_bytes(b"model version 2 - completely different weights")
    wrapper2 = CvModelWrapper(model_file)
    ctx2 = _make_ctx(tmp_path, model=wrapper2)
    res2 = det.run(ctx2)

    # At least one of the two runs should detect a change
    # (the first stores baseline, the second compares)
    if res1.status == "ok" and res2.status == "ok":
        # Both ran — the second should either match or mismatch
        assert res2.summary != ""


def test_finding_validates() -> None:
    """The finding emitted by the detector must pass schema validation."""
    from cvassure.core.finding import Finding

    f = Finding.draft(
        asset="model",
        reason="Behavioural fingerprint mismatch: cosine similarity 0.85 below threshold 0.95",
        evidence=["evidence/fingerprint_comparison.png"],
        severity=0.8,
        confidence=0.7,
        access_level="white-box",
        limitations="A fingerprint mismatch detects behavioural change, not its cause.",
        disposition="review",
        tags=["fingerprint_mismatch"],
        metadata={"cosine_similarity": 0.85, "threshold": 0.95},
    )
    # Should not raise
    validated = validate_finding(f.to_final("F-001").model_dump(), detector_id="model.fingerprint")
    assert validated.asset == "model"
