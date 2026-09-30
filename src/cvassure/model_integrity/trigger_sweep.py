"""Patch-library trigger sweep detector (black-box).

Applies a library of known patch triggers to clean images and checks
whether the model's prediction flips to a target class. Emits a
``trigger_sweep_hit`` finding with ``patch_library`` link hints when
a known trigger is detected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import numpy as np

from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.finding import Finding, LinkHints, TriggerHint


class TriggerSweepDetector(Detector):
    """Black-box patch-library trigger sweep.

    Loads a library of known patch images, applies each to a set of
    clean reference images, and checks whether the model's prediction
    changes. When a flip is detected the finding carries ``patch_library``
    link hints so the cross-asset linker can match it to data findings.
    """

    id: ClassVar[str] = "model.trigger_sweep"
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

        # Load patch library
        patch_library_path = self._patch_library_path(ctx)
        if patch_library_path is None or not patch_library_path.is_dir():
            res.status = "skipped"
            res.skipped_reason = "no patch library directory configured"
            return res

        patches = self._load_patches(patch_library_path)
        if not patches:
            res.status = "skipped"
            res.skipped_reason = "patch library is empty"
            return res

        # Generate clean reference images
        rng = np.random.RandomState(ctx.seed)
        clean_images = rng.randn(5, 3, 32, 32).astype(np.float32)

        # Get baseline predictions
        baseline_preds = ctx.model.predict(clean_images)
        if not baseline_preds:
            res.status = "skipped"
            res.skipped_reason = "model predict returned Unavailable"
            return res
        baseline_preds = np.asarray(baseline_preds)
        if baseline_preds.ndim == 1:
            baseline_preds = baseline_preds.reshape(1, -1)
        baseline_classes = baseline_preds.argmax(axis=1)

        # Sweep each patch
        hits: list[dict[str, Any]] = []
        for patch_id, patch_img in patches.items():
            patched_images = self._apply_patch(clean_images, patch_img)
            patched_preds = ctx.model.predict(patched_images)
            if not patched_preds:
                continue
            patched_preds = np.asarray(patched_preds)
            if patched_preds.ndim == 1:
                patched_preds = patched_preds.reshape(1, -1)
            patched_classes = patched_preds.argmax(axis=1)

            # Check for flips
            flips = patched_classes != baseline_classes
            if flips.any():
                target_class = int(patched_classes[flips][0])
                success_rate = float(flips.mean())
                hits.append(
                    {
                        "patch_id": patch_id,
                        "target_class": target_class,
                        "success_rate": success_rate,
                        "patch_img": patch_img,
                    }
                )

        if not hits:
            res.summary = f"swept {len(patches)} patches, no trigger detected"
            return res

        # Report the strongest hit
        best = max(hits, key=lambda h: h["success_rate"])
        patch_id = best["patch_id"]
        target_class = best["target_class"]
        success_rate = best["success_rate"]

        # Write evidence: patch template
        evidence_rel = f"evidence/patch_{patch_id}.png"
        self._save_patch_evidence(ctx, best["patch_img"], evidence_rel)

        res.findings.append(
            Finding.draft(
                asset="model",
                reason=(
                    f"Patch-library sweep hit patch {patch_id} on class {target_class} "
                    f"with attack success rate {success_rate:.2f}"
                ),
                evidence=[evidence_rel],
                severity=0.7 + 0.2 * success_rate,
                confidence=0.6 + 0.3 * success_rate,
                access_level=ctx.model.declare_access_tier(),
                limitations=(
                    "Patch-library sweep detects known triggers only. Novel or "
                    "adaptive triggers are not detected by this method."
                ),
                disposition="review",
                class_label=target_class,
                sample_count=len(hits),
                tags=["trigger_sweep_hit"],
                link_hints=LinkHints(
                    target_class=target_class,
                    trigger=TriggerHint(kind="patch_library", patch_id=patch_id),
                    location_bbox=[0.1, 0.1, 0.3, 0.3],
                    patch_template_path=evidence_rel,
                ),
                metadata={
                    "patch_id": patch_id,
                    "target_class": target_class,
                    "attack_success_rate": round(success_rate, 4),
                    "n_patches_swept": len(patches),
                    "n_hits": len(hits),
                },
            )
        )
        res.summary = f"sweep hit patch {patch_id} on class {target_class} (ASR {success_rate:.2f})"
        return res

    def _patch_library_path(self, ctx: AuditContext) -> Path | None:
        """Resolve the patch library directory from config or default."""
        config_path = ctx.config.get("patch_library")
        if config_path:
            return Path(config_path)
        # Default: look for patches/ next to the model
        if ctx.model is not None:
            default = ctx.model.model_path.parent / "patches"
            if default.is_dir():
                return default
        return None

    def _load_patches(self, path: Path) -> dict[str, np.ndarray]:
        """Load all patch images from the library directory."""
        patches: dict[str, np.ndarray] = {}
        for img_path in sorted(path.glob("*.png")):
            patch_id = img_path.stem
            try:
                from PIL import Image

                with Image.open(img_path) as im:
                    arr = np.asarray(im.convert("RGB"), dtype=np.float32)
                patches[patch_id] = arr
            except Exception:
                continue
        return patches

    def _apply_patch(self, images: np.ndarray, patch: np.ndarray) -> np.ndarray:
        """Apply a patch to a batch of images at a fixed location."""
        patched = images.copy()
        ph, pw = patch.shape[:2]
        # Place patch in the bottom-right corner
        h, w = images.shape[-2:]
        y = max(0, h - ph)
        x = max(0, w - pw)
        # Normalize patch to image range
        patch_resized = self._resize_patch(patch, min(ph, h), min(pw, w))
        patched[..., y : y + patch_resized.shape[0], x : x + patch_resized.shape[1]] = patch_resized
        return patched

    def _resize_patch(self, patch: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
        """Simple nearest-neighbor resize of a patch."""
        h, w = patch.shape[:2]
        ys = np.linspace(0, h - 1, target_h).astype(int)
        xs = np.linspace(0, w - 1, target_w).astype(int)
        return patch[ys][:, xs]

    def _save_patch_evidence(self, ctx: AuditContext, patch: np.ndarray, rel_path: str) -> None:
        """Save the patch as a PNG evidence file."""
        from cvassure.core.imaging import write_png

        h, w = patch.shape[:2]
        # Convert float to uint8
        patch_uint8 = np.clip(patch, 0, 255).astype(np.uint8)
        pixels = [[tuple(patch_uint8[y, x]) for x in range(w)] for y in range(h)]
        out_path = ctx.out_dir / rel_path
        write_png(out_path, w, h, pixels)
