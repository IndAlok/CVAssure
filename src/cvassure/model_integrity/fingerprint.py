"""Behavioural fingerprint detector.

Runs a fixed reference battery through the model and compares the
behavioural fingerprint against a stored reference. Detects model
swaps by identifying when the fingerprint changes.
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np

from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.finding import Finding


class FingerprintDetector(Detector):
    """Detect model swaps via behavioural fingerprint comparison.

    The fingerprint is computed by running a deterministic reference
    battery through the model and collecting the output probability
    vectors. The cosine similarity between the computed fingerprint and
    a stored reference determines whether the model has changed.
    """

    id: ClassVar[str] = "model.fingerprint"
    asset: ClassVar[str] = "model"
    owner: ClassVar[str] = "model"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset({"logits"})

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.model is None:
            res.status = "skipped"
            res.skipped_reason = "no model wrapper is loaded"
            return res

        # Generate deterministic reference battery from seed
        rng = np.random.RandomState(ctx.seed)
        reference_inputs = rng.randn(10, 3, 32, 32).astype(np.float32)

        # Run inference
        predictions = ctx.model.predict(reference_inputs)
        if not predictions:
            res.status = "skipped"
            res.skipped_reason = "model predict returned Unavailable"
            return res

        predictions = np.asarray(predictions)
        if predictions.ndim == 1:
            predictions = predictions.reshape(1, -1)

        # Compute fingerprint: mean prediction vector
        fingerprint = predictions.mean(axis=0)

        # Look for reference fingerprint file
        model_path = ctx.model.model_path
        fingerprint_path = model_path.with_suffix(model_path.suffix + ".fingerprint.npy")

        if not fingerprint_path.is_file():
            # No reference — store the current fingerprint as the baseline
            np.save(fingerprint_path, fingerprint)
            res.summary = "no reference fingerprint stored current as baseline"
            return res

        # Load reference and compare
        try:
            reference = np.load(fingerprint_path, allow_pickle=False)
        except (OSError, ValueError):
            res.status = "skipped"
            res.skipped_reason = "cannot load reference fingerprint file"
            return res

        similarity = self._cosine_similarity(fingerprint, reference)
        threshold = float(ctx.config.get("fingerprint_threshold", 0.95))

        if similarity >= threshold:
            res.summary = f"fingerprint match (cosine similarity {similarity:.4f})"
            return res

        res.findings.append(
            Finding.draft(
                asset="model",
                reason=(
                    f"Behavioural fingerprint mismatch: cosine similarity {similarity:.4f} "
                    f"is below threshold {threshold:.2f} — model may have been swapped"
                ),
                evidence=[],
                severity=0.8,
                confidence=0.7,
                access_level=ctx.model.declare_access_tier(),
                limitations=(
                    "A fingerprint mismatch detects behavioural change, not its cause. "
                    "Quantization, fine-tuning, or a different input preprocessing "
                    "pipeline can also change the fingerprint."
                ),
                disposition="review",
                tags=["fingerprint_mismatch"],
                metadata={
                    "cosine_similarity": round(similarity, 6),
                    "threshold": threshold,
                    "fingerprint_shape": list(fingerprint.shape),
                },
            )
        )
        res.summary = f"fingerprint MISMATCH (similarity {similarity:.4f})"
        return res

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two vectors."""
        a = a.flatten()
        b = b.flatten()
        if a.shape != b.shape:
            return 0.0
        dot = float(np.dot(a, b))
        norm_a = float(np.linalg.norm(a))
        norm_b = float(np.linalg.norm(b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
