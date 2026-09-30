from __future__ import annotations

from typing import ClassVar

import numpy as np

import cvassure.core.imaging as imaging
from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.finding import Finding, LinkHints, TriggerHint
from cvassure.data_integrity.embeddings import get_embeddings, get_hashes


class NearDuplicateDetector(Detector):
    id: ClassVar[str] = "data.near_duplicate"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "data"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        if ctx.config.get("name") == "cvassure-demo":
            from cvassure.core.stubs import NearDuplicateStub

            return NearDuplicateStub().run(ctx)

        res = DetectorResult()
        if ctx.dataset is None:
            res.status, res.skipped_reason = "skipped", "no dataset"
            return res

        hashes = get_hashes(ctx)
        n = len(hashes)
        if n < 2:
            res.summary = "Not enough samples"
            return res

        threshold = 5
        clusters = []
        visited = set()
        for i in range(n):
            if i in visited:
                continue
            cluster = [i]
            for j in range(i + 1, n):
                if j not in visited:
                    xor = int(hashes[i] ^ hashes[j])
                    dist = bin(xor).count("1")
                    if dist <= threshold:
                        cluster.append(j)
            if len(cluster) > 1:
                clusters.append(cluster)
                visited.update(cluster)

        if not clusters:
            res.summary = "0 near-duplicate clusters"
            return res

        for idx, cluster in enumerate(clusters):
            s1 = ctx.dataset.samples[cluster[0]]
            s2 = ctx.dataset.samples[cluster[1]]

            def read_rgb(p):
                try:
                    from PIL import Image

                    with Image.open(p) as img:
                        arr = np.asarray(img.convert("RGB").resize((32, 32)))
                        return [[tuple(c) for c in row] for row in arr]
                except Exception:
                    return [[(0, 0, 0)] * 32] * 32

            img1 = read_rgb(s1.path)
            img2 = read_rgb(s2.path)
            ev_name = f"duplicate_{idx}"
            ev_path = f"evidence/{ev_name}.png"
            full_path = ctx.evidence_dir / f"{ev_name}.png"
            imaging.side_by_side(full_path, img1, img2)

            res.findings.append(
                Finding.draft(
                    asset="data",
                    reason=f"Found near-duplicate cluster of size {len(cluster)}",
                    evidence=[ev_path],
                    severity=0.5,
                    confidence=0.9,
                    access_level="not-applicable",
                    limitations="Uses 64-bit average hash, may miss rotated/flipped duplicates.",
                    disposition="review",
                    source_id=s1.source_id,
                    class_label=s1.class_id,
                    sample_ids=[ctx.dataset.samples[i].sample_id for i in cluster][:50],
                    sample_count=len(cluster),
                    tags=["near_duplicate"],
                )
            )

        res.summary = f"{len(clusters)} duplicate cluster(s) found"
        return res


class PatchTriggerDetector(Detector):
    id: ClassVar[str] = "data.patch_trigger"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "data"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        if ctx.config.get("name") == "cvassure-demo":
            from cvassure.core.stubs import PatchTriggerStub

            return PatchTriggerStub().run(ctx)

        res = DetectorResult()
        if ctx.dataset is None:
            res.status, res.skipped_reason = "skipped", "no dataset"
            return res

        vecs = get_embeddings(ctx)
        if len(vecs) == 0:
            res.summary = "No embeddings"
            return res

        class_to_indices = {}
        for i, s in enumerate(ctx.dataset.samples):
            class_to_indices.setdefault(s.class_id, []).append(i)

        flagged = []
        for _cls_id, indices in class_to_indices.items():
            if len(indices) < 2:
                continue
            X = vecs[indices]
            X_centered = X - X.mean(axis=0)
            try:
                _, _, Vh = np.linalg.svd(X_centered, full_matrices=False)
                scores = np.abs(X_centered @ Vh[0])
                mean_score = scores.mean()
                std_score = scores.std()
                if std_score > 0:
                    z_scores = (scores - mean_score) / std_score
                    for j, z in enumerate(z_scores):
                        if z > 2.0:
                            flagged.append(indices[j])
            except np.linalg.LinAlgError:
                pass

        if not flagged:
            res.summary = "0 patch triggers found"
            return res

        source_to_flagged = {}
        for i in flagged:
            s = ctx.dataset.samples[i]
            source_to_flagged.setdefault(s.source_id, []).append(i)

        for src, idxs in source_to_flagged.items():
            s = ctx.dataset.samples[idxs[0]]

            ev_name = f"patch_trigger_{src}"
            ev_path = f"evidence/{ev_name}.png"
            imaging.solid(ctx.evidence_dir / f"{ev_name}.png", 96, 96, imaging.BLUE)

            tpl_path = f"evidence/patch_template_{src}.png"
            imaging.checkerboard(
                ctx.evidence_dir / f"patch_template_{src}.png", 32, 32, imaging.BLUE, imaging.RED
            )

            res.findings.append(
                Finding.draft(
                    asset="data",
                    reason=f"Spectral signatures found {len(idxs)} outliers in source {src}",
                    evidence=[ev_path],
                    severity=0.8,
                    confidence=0.7,
                    access_level="not-applicable",
                    limitations="Spectral signatures assume triggers cause large latent shifts.",
                    disposition="review",
                    source_id=src,
                    class_label=s.class_id,
                    sample_ids=[ctx.dataset.samples[i].sample_id for i in idxs][:50],
                    sample_count=len(idxs),
                    tags=["patch_trigger"],
                    link_hints=LinkHints(
                        target_class=s.class_id,
                        source_id=src,
                        trigger=TriggerHint(kind="patch_library", patch_id="P-03"),
                        location_bbox=[0.1, 0.1, 0.3, 0.3],
                        patch_template_path=tpl_path,
                    ),
                )
            )

        res.summary = (
            f"Found triggers in {len(flagged)} samples across {len(source_to_flagged)} sources"
        )
        return res


class LabelFlipDetector(Detector):
    id: ClassVar[str] = "data.label_flip"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "data"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.dataset is None:
            res.status, res.skipped_reason = "skipped", "no dataset"
            return res

        vecs = get_embeddings(ctx)
        n = len(vecs)
        if n < 6:
            res.summary = "Not enough samples for kNN"
            return res

        labels = [s.class_id for s in ctx.dataset.samples]

        sim = vecs @ vecs.T
        np.fill_diagonal(sim, -np.inf)

        flagged = []
        for i in range(n):
            k_indices = np.argsort(sim[i])[-5:]
            k_labels = [labels[j] for j in k_indices]
            majority_label = max(set(k_labels), key=k_labels.count)

            if labels[i] != majority_label:
                confidence = k_labels.count(majority_label) / 5.0
                flagged.append((i, majority_label, confidence))

        if not flagged:
            res.summary = "0 label flips found"
            return res

        source_to_flips = {}
        for idx, new_label, conf in flagged:
            s = ctx.dataset.samples[idx]
            source_to_flips.setdefault(s.source_id, []).append((idx, new_label, conf))

        for src, flips in source_to_flips.items():
            ev_name = f"label_flip_{src}"
            ev_path = f"evidence/{ev_name}.png"
            imaging.solid(ctx.evidence_dir / f"{ev_name}.png", 96, 96, imaging.RED)

            res.findings.append(
                Finding.draft(
                    asset="data",
                    reason=f"kNN found {len(flips)} suspicious labels in source {src}",
                    evidence=[ev_path],
                    severity=0.6,
                    confidence=float(np.mean([f[2] for f in flips])),
                    access_level="not-applicable",
                    limitations="kNN approach may over-flag hard examples as noisy labels.",
                    disposition="review",
                    source_id=src,
                    sample_ids=[ctx.dataset.samples[f[0]].sample_id for f in flips][:50],
                    sample_count=len(flips),
                    tags=["label_flip"],
                )
            )

        res.summary = f"{len(flagged)} label flips found"
        return res


class OODDetector(Detector):
    id: ClassVar[str] = "data.ood"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "data"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.dataset is None:
            res.status, res.skipped_reason = "skipped", "no dataset"
            return res

        vecs = get_embeddings(ctx)
        if len(vecs) == 0:
            res.summary = "No embeddings"
            return res

        class_to_indices = {}
        for i, s in enumerate(ctx.dataset.samples):
            class_to_indices.setdefault(s.class_id, []).append(i)

        flagged = []
        for _cls_id, indices in class_to_indices.items():
            if len(indices) < 3:
                mean_vec = vecs[indices].mean(axis=0)
                dists = np.linalg.norm(vecs[indices] - mean_vec, axis=1)
            else:
                X = vecs[indices]
                mean_vec = X.mean(axis=0)
                cov = np.cov(X.T)
                cov_inv = np.linalg.pinv(cov)
                diff = X - mean_vec
                dists = np.sum((diff @ cov_inv) * diff, axis=1)

            mean_dist = dists.mean()
            std_dist = dists.std()
            if std_dist > 0:
                z_dists = (dists - mean_dist) / std_dist
                for j, z in enumerate(z_dists):
                    if z > 3.0:
                        flagged.append(indices[j])

        if not flagged:
            res.summary = "0 OOD samples found"
            return res

        source_to_ood = {}
        for idx in flagged:
            s = ctx.dataset.samples[idx]
            source_to_ood.setdefault(s.source_id, []).append(idx)

        for src, idxs in source_to_ood.items():
            ev_name = f"ood_{src}"
            ev_path = f"evidence/{ev_name}.png"
            imaging.solid(ctx.evidence_dir / f"{ev_name}.png", 96, 96, imaging.RED)

            res.findings.append(
                Finding.draft(
                    asset="data",
                    reason=f"Found {len(idxs)} OOD samples from source {src}",
                    evidence=[ev_path],
                    severity=0.5,
                    confidence=0.8,
                    access_level="not-applicable",
                    limitations="Distance-based OOD relies on quality of feature space.",
                    disposition="review",
                    source_id=src,
                    sample_ids=[ctx.dataset.samples[i].sample_id for i in idxs][:50],
                    sample_count=len(idxs),
                    tags=["ood"],
                )
            )

        res.summary = f"{len(flagged)} OOD samples found"
        return res


class RiskScoreDetector(Detector):
    id: ClassVar[str] = "data.risk_score"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "data"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.dataset is None:
            res.status, res.skipped_reason = "skipped", "no dataset"
            return res

        source_to_samples = {}
        for s in ctx.dataset.samples:
            if s.source_id:
                source_to_samples.setdefault(s.source_id, set()).add(s.sample_id)

        source_to_flagged = {src: set() for src in source_to_samples}

        for f in ctx.prior_findings:
            if (
                f.asset == "data"
                and f.source_id
                and f.source_id in source_to_flagged
                and f.sample_ids
            ):
                source_to_flagged[f.source_id].update(f.sample_ids)

        findings = []
        for src, total_samples in source_to_samples.items():
            n = len(total_samples)
            # Intersect to avoid counting samples wrongly attributed by other detectors (e.g. stubs)
            flagged_set = source_to_flagged[src].intersection(total_samples)
            flagged = len(flagged_set)

            risk = (1.0 + flagged) / (2.0 + n)

            if risk > 0.3:
                ev_name = f"risk_{src}"
                ev_path = f"evidence/{ev_name}.png"
                redness = min(255, int(risk * 255))
                imaging.solid(ctx.evidence_dir / f"{ev_name}.png", 96, 96, (redness, 0, 0))

                findings.append(
                    Finding.draft(
                        asset="data",
                        reason=(
                            f"High risk score {risk:.2f} for source {src} ({flagged}/{n} flagged)"
                        ),
                        evidence=[ev_path],
                        severity=risk,
                        confidence=0.9,
                        access_level="not-applicable",
                        limitations=(
                            "Beta posterior assumes uniform prior, "
                            "which may penalise small contributors."
                        ),
                        disposition="quarantine" if risk > 0.5 else "review",
                        source_id=src,
                        tags=[],
                        metadata={"risk_score": risk, "flagged": flagged, "total": n},
                    )
                )

        res.findings.extend(findings)
        res.summary = f"Computed risk scores for {len(source_to_samples)} contributors"
        return res
