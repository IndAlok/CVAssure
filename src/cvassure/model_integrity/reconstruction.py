"""Neural-Cleanse style trigger reconstruction detector (white-box).

Reconstructs a trigger mask for each class by optimizing a mask that
causes the model to classify inputs as that class. Uses the
median - 2*MAD outlier test to flag anomalously small triggers,
indicating a backdoor.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np

from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.finding import Finding, LinkHints, TriggerHint
from cvassure.core.imaging import RED, write_png


class ReconstructionDetector(Detector):
    """White-box trigger reconstruction via mask optimization.

    For each class, optimizes a mask such that the model classifies
    masked inputs as that class. The L1 norm of each optimized mask
    is computed and the median - 2*MAD test flags classes with
    anomalously small triggers — the Neural-Cleanse outlier signal.
    """

    id: ClassVar[str] = "model.reconstruction"
    asset: ClassVar[str] = "model"
    owner: ClassVar[str] = "model"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset({"weights", "gradients"})

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.model is None:
            res.status = "skipped"
            res.skipped_reason = "no model wrapper is loaded"
            return res

        # Determine number of classes from the model
        n_classes = self._infer_n_classes(ctx)
        if n_classes is None or n_classes < 2:
            res.status = "skipped"
            res.skipped_reason = "cannot infer number of classes from model"
            return res

        # Reconstruct trigger for each class
        mask_norms: dict[int, float] = {}
        mask_paths: dict[int, str] = {}

        for class_id in range(n_classes):
            mask_l1, mask_img = self._reconstruct_trigger(ctx, class_id, n_classes)
            if mask_l1 is not None:
                mask_norms[class_id] = mask_l1
                # Save mask as evidence
                rel_path = f"evidence/recon_mask_class_{class_id}.png"
                self._save_mask_evidence(ctx, mask_img, rel_path)
                mask_paths[class_id] = rel_path

        if len(mask_norms) < 2:
            res.status = "skipped"
            res.skipped_reason = "too few classes reconstructed for outlier test"
            return res

        # Outlier test: median - 2*MAD
        norms = np.array(list(mask_norms.values()))
        median = float(np.median(norms))
        mad = float(np.median(np.abs(norms - median)))
        threshold = median - 2.0 * mad

        flagged_classes = [
            cid for cid, norm in mask_norms.items() if norm < threshold
        ]

        if not flagged_classes:
            res.summary = (
                f"reconstructed {len(mask_norms)} classes, no anomalously small triggers"
            )
            return res

        # Report the most anomalous class
        flagged_classes.sort(key=lambda c: mask_norms[c])
        top_class = flagged_classes[0]
        top_norm = mask_norms[top_class]

        res.findings.append(
            Finding.draft(
                asset="model",
                reason=(
                    f"Reconstructed trigger for class {top_class} is anomalously small "
                    f"(L1 norm {top_norm:.4f}, median {median:.4f}, MAD {mad:.4f}, "
                    f"threshold {threshold:.4f}) — Neural-Cleanse style outlier"
                ),
                evidence=[mask_paths[top_class]],
                severity=0.85,
                confidence=0.7,
                access_level="white-box",
                limitations=(
                    "Neural-Cleanse style reconstruction is unreliable for blended or "
                    "input-aware triggers. A small mask suggests but does not prove a backdoor."
                ),
                disposition="review",
                class_label=top_class,
                tags=["trigger_reconstructed"],
                link_hints=LinkHints(
                    target_class=top_class,
                    trigger=TriggerHint(
                        kind="reconstructed",
                        mask_path=mask_paths[top_class],
                    ),
                    location_bbox=[0.1, 0.1, 0.3, 0.3],
                ),
                metadata={
                    "flagged_classes": flagged_classes,
                    "mask_norms": {str(k): round(v, 6) for k, v in mask_norms.items()},
                    "median": round(median, 6),
                    "mad": round(mad, 6),
                    "threshold": round(threshold, 6),
                },
            )
        )
        res.summary = (
            f"class {top_class} flagged: anomalously small trigger "
            f"(L1 {top_norm:.4f} < threshold {threshold:.4f})"
        )
        return res

    def _infer_n_classes(self, ctx: AuditContext) -> int | None:
        """Infer the number of output classes from the model."""
        rng = np.random.RandomState(ctx.seed)
        sample_input = rng.randn(1, 3, 32, 32).astype(np.float32)
        output = ctx.model.predict(sample_input)
        if not output:
            return None
        output = np.asarray(output)
        if output.ndim == 2:
            return int(output.shape[1])
        if output.ndim == 1:
            return int(output.shape[0])
        return None

    def _reconstruct_trigger(
        self, ctx: AuditContext, target_class: int, n_classes: int
    ) -> tuple[float | None, np.ndarray | None]:
        """Reconstruct a trigger mask for a target class.

        Optimizes a mask such that the model classifies masked inputs
        as the target class. Returns the L1 norm of the optimized mask
        and the mask image.
        """
        rng = np.random.RandomState(ctx.seed + target_class)
        n_samples = 5
        images = rng.randn(n_samples, 3, 32, 32).astype(np.float32)

        # Simple iterative mask optimization
        # Start with a zero mask, gradient ascent on target class logit
        mask = np.zeros((3, 32, 32), dtype=np.float32)
        lr = 0.1
        n_steps = 50

        for step in range(n_steps):
            # Apply mask
            masked = images + mask[None]

            # Get gradients
            grads = ctx.model.gradients(masked)
            if not grads:
                return None, None
            grads = np.asarray(grads)

            # Compute loss gradient: we want to maximize target class logit
            # Simple approach: use the gradient of the target class logit w.r.t. input
            # For a real implementation this would use torch.autograd
            # Here we use a finite-difference approximation for generality
            eps = 0.01
            grad_mask = np.zeros_like(mask)
            for c in range(3):
                for i in range(0, 32, 4):  # subsample for speed
                    for j in range(0, 32, 4):
                        masked_plus = masked.copy()
                        masked_plus[:, c, i, j] += eps
                        out_plus = ctx.model.predict(masked_plus)
                        if not out_plus:
                            continue
                        out_plus = np.asarray(out_plus)
                        if out_plus.ndim == 2:
                            target_logit_plus = out_plus[:, target_class].mean()
                        else:
                            target_logit_plus = out_plus.mean()

                        masked_minus = masked.copy()
                        masked_minus[:, c, i, j] -= eps
                        out_minus = ctx.model.predict(masked_minus)
                        if not out_minus:
                            continue
                        out_minus = np.asarray(out_minus)
                        if out_minus.ndim == 2:
                            target_logit_minus = out_minus[:, target_class].mean()
                        else:
                            target_logit_minus = out_minus.mean()

                        grad_mask[c, i, j] = (target_logit_plus - target_logit_minus) / (2 * eps)

            # Update mask
            mask += lr * grad_mask

            # Clip mask to valid range
            mask = np.clip(mask, -2.0, 2.0)

            # Decay learning rate
            lr *= 0.95

        mask_l1 = float(np.abs(mask).sum())
        return mask_l1, mask

    def _save_mask_evidence(
        self, ctx: AuditContext, mask: np.ndarray | None, rel_path: str
    ) -> None:
        """Save the reconstructed mask as a PNG heatmap."""
        if mask is None:
            return
        # Convert mask to a visual heatmap
        mask_mean = mask.mean(axis=0) if mask.ndim == 3 else mask
        h, w = mask_mean.shape
        # Normalize to 0-255
        m_min, m_max = float(mask_mean.min()), float(mask_mean.max())
        if m_max > m_min:
            normalized = (mask_mean - m_min) / (m_max - m_min)
        else:
            normalized = np.zeros_like(mask_mean)
        # Use red channel for the heatmap
        pixels = [
            [(int(normalized[y, x] * 255), 0, 0) for x in range(w)]
            for y in range(h)
        ]
        out_path = ctx.out_dir / rel_path
        write_png(out_path, w, h, pixels)
