"""Cross-asset linking. Evidence in, links out, or nothing.

Decides whether a model trigger finding and a data patch finding refer to the
same visual trigger, using only the `link_hints` both sides emitted. It does not
read ground truth. It may print nothing.

The score uses the evidence both sides actually have, then renormalises the
configured weights over the components that exist. A black-box sweep with a
patch id and a class links on identity alone.

IoU and NCC are computed with NumPy. OpenCV is not a dependency.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from cvassure.core.config import LinkConfig
from cvassure.core.finding import Escalation, Finding


@dataclass
class Link:
    data_finding: str
    model_finding: str
    score: float
    components: dict[str, float] = field(default_factory=dict)
    weights_used: dict[str, float] = field(default_factory=dict)
    evidence: str | None = None


def iou(a: Sequence[float], b: Sequence[float]) -> float:
    """IoU of two normalised [x, y, w, h] boxes."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix0, iy0 = max(ax, bx), max(ay, by)
    ix1, iy1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return float(inter / union) if union > 0 else 0.0


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    """Normalised cross-correlation, resampled to a common grid. Range [-1, 1].

    Two flat images give 0/0, which is undefined, so it returns 0.0. A constant
    patch carries no pattern, and "no evidence" is the honest score.
    """
    if a.size == 0 or b.size == 0:
        return 0.0
    grid = (min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1]))
    if grid[0] < 2 or grid[1] < 2:
        return 0.0

    def prep(img: np.ndarray) -> np.ndarray:
        out = np.asarray(img, dtype=np.float64)
        if out.ndim == 3:
            out = out.mean(axis=2)
        if out.shape != grid:
            ys = np.linspace(0, out.shape[0] - 1, grid[0])
            xs = np.linspace(0, out.shape[1] - 1, grid[1])
            out = np.array(
                [[out[int(round(y)), int(round(x))] for x in xs] for y in ys], dtype=np.float64
            )
        return out

    pa, pb = prep(a), prep(b)
    pa -= pa.mean()
    pb -= pb.mean()
    denom = float(np.sqrt((pa * pa).sum()) * np.sqrt((pb * pb).sum()))
    if denom == 0.0:
        return 0.0
    return float(np.clip((pa * pb).sum() / denom, -1.0, 1.0))


def _read_gray(path: Path) -> np.ndarray | None:
    """Read a greyscale array from a `.npy`, or from a PNG via an optional Pillow.

    Numpy reads `.npy` natively, with no dependency. PNG needs a decoder, and
    Pillow is deliberately **not** a core dependency, so the import is attempted
    lazily. If Pillow is installed, the `pattern` component can read PNG templates.
    If it is not, that component is absent.
    """
    if not path.is_file():
        return None
    suffix = path.suffix.lower()
    if suffix == ".npy":
        try:
            return np.load(path, allow_pickle=False)
        except (OSError, ValueError):
            return None
    if suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"):
        try:
            from PIL import Image  # optional. See the docstring.
        except ImportError:
            return None
        try:
            with Image.open(path) as im:
                return np.asarray(im.convert("L"), dtype=np.float64)
        except (OSError, ValueError):
            return None
    return None


def _evidence_path(evidence_dir: Path, rel: str | None) -> Path | None:
    """Resolve a `link_hints` path to a real file.

    Those paths are relative to `out/`, the same rule as a Finding's `evidence`
    field, so `evidence/foo.npy` lives at `out/evidence/foo.npy`. Resolving them
    against `evidence_dir` directly would look for `out/evidence/evidence/foo.npy`
    and silently find nothing, which reads as "no pattern evidence" rather than
    as the bug it is.
    """
    if not rel or rel.startswith(("/", "~")) or (len(rel) > 1 and rel[1] == ":"):
        return None
    if ".." in rel.replace("\\", "/").split("/"):
        return None
    root = evidence_dir.parent.resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _pair_components(
    data: Finding, model: Finding, cfg: LinkConfig, evidence_dir: Path
) -> dict[str, float]:
    dh, mh = data.link_hints, model.link_hints
    if dh is None or mh is None:
        return {}

    # 1. class gate. Both sides must agree on the class or the score is zero.
    if (
        dh.target_class is not None
        and mh.target_class is not None
        and dh.target_class != mh.target_class
    ):
        return {}

    out: dict[str, float] = {}

    # 2. identity
    d_id = dh.trigger.patch_id
    m_id = mh.trigger.patch_id
    if d_id and m_id:
        out["identity"] = 1.0 if d_id == m_id else 0.0

    # 3. overlap
    if dh.location_bbox and mh.location_bbox:
        out["overlap"] = iou(dh.location_bbox, mh.location_bbox)

    # 4. pattern
    d_tpl = dh.patch_template_path
    m_tpl = mh.patch_template_path or mh.trigger.pattern_path
    if d_tpl and m_tpl:
        a = _read_gray(_evidence_path(evidence_dir, d_tpl))
        b = _read_gray(_evidence_path(evidence_dir, m_tpl))
        if a is not None and b is not None:
            out["pattern"] = max(0.0, ncc(a, b))
    return out


def _renormalise(components: dict[str, float], cfg: LinkConfig) -> tuple[float, dict[str, float]]:
    """Renormalise the configured weights over the components that exist.

    A link scored on identity alone uses weight 1.0 on identity. Printing the
    configured weight next to the used weight is the difference between an
    honest score and one that looks stronger than it is.
    """
    if not components:
        return 0.0, {}
    configured = {
        "identity": cfg.identity_weight,
        "overlap": cfg.overlap_weight,
        "pattern": cfg.pattern_weight,
    }
    used = {k: configured.get(k, 0.0) for k in components}
    total = sum(used.values())
    if total <= 0:
        # Every present component has weight 0. Equal split is the least-bad
        # reading. tau_link still decides, and weights_used records what happened.
        used = dict.fromkeys(components, 1.0)
        total = float(len(used))
    weights = {k: v / total for k, v in used.items()}
    return float(sum(components[k] * weights[k] for k in components)), weights


def find_links(
    findings: Sequence[Finding], cfg: LinkConfig, evidence_dir: Path
) -> tuple[list[Link], dict[str, Any]]:
    """Every pair that clears tau_link, plus a report of what was considered."""
    data_side = [
        f
        for f in findings
        if f.asset == "data" and f.link_hints and f.link_hints.trigger.kind == "patch_library"
    ]
    model_side = [
        f
        for f in findings
        if f.asset == "model" and f.link_hints and f.link_hints.trigger.kind == "reconstructed"
    ]
    # A model sweep that found a library patch links on identity, so include those too.
    model_side += [
        f
        for f in findings
        if f.asset == "model"
        and f.link_hints
        and f.link_hints.trigger.kind == "patch_library"
        and f not in model_side
    ]

    links: list[Link] = []
    considered = 0
    for df in data_side:
        for mf in model_side:
            considered += 1
            comps = _pair_components(df, mf, cfg, evidence_dir)
            if not comps:
                continue
            score, weights = _renormalise(comps, cfg)
            if score >= cfg.tau_link:
                links.append(
                    Link(
                        data_finding=df.id or "",
                        model_finding=mf.id or "",
                        score=score,
                        components=comps,
                        weights_used=weights,
                    )
                )
    report = {
        "tau_link": cfg.tau_link,
        "weights": {
            "identity": cfg.identity_weight,
            "overlap": cfg.overlap_weight,
            "pattern": cfg.pattern_weight,
        },
        "calibration": cfg.calibration,
        "pairs_considered": considered,
        "pairs_linked": len(links),
    }
    return links, report


def apply_links(
    findings: Sequence[Finding], links: Sequence[Link], evidence_dir: Path
) -> list[Finding]:
    """Cross-link, escalate model severity with noisy-OR, record the escalation."""
    by_id = {f.id: f for f in findings if f.id}
    updates: dict[str, dict[str, Any]] = {}

    for link in links:
        df, mf = by_id.get(link.data_finding), by_id.get(link.model_finding)
        if df is None or mf is None:
            continue

        before = mf.severity
        after = min(1.0, 1.0 - (1.0 - mf.severity) * (1.0 - df.severity))

        merged = sorted(
            {*updates.get(df.id or "", {}).get("linked_findings", df.linked_findings), mf.id or ""}
        )
        m_merged = sorted(
            {*updates.get(mf.id or "", {}).get("linked_findings", mf.linked_findings), df.id or ""}
        )

        note = (
            f"Linked to {df.id} on evidence {sorted(link.components)}. "
            "pattern similarity was not available."
            if "pattern" not in link.components
            else ""
        )
        # Typed sub-models, not raw dicts: `model_copy` skips validation, so a
        # dict here would survive until something reads `.escalated.escalated`.
        updates[df.id or ""] = {
            "linked_findings": merged,
            "escalation": Escalation(
                escalated=False,
                severity_before=df.severity,
                linked_to=[mf.id or ""],
                method="link",
            ),
        }
        updates[mf.id or ""] = {
            "linked_findings": m_merged,
            "severity": after,
            "escalation": Escalation(
                escalated=after > before,
                severity_before=before,
                linked_to=[df.id or ""],
                method="noisy-or",
            ),
            "limitations": (mf.limitations + note).strip()[:300] if note else mf.limitations,
        }

        fig = _link_figure(df, mf, link, evidence_dir)
        if fig:
            link.evidence = fig

    out: list[Finding] = []
    for f in findings:
        upd = updates.get(f.id or "")
        out.append(f.model_copy(update=upd) if upd else f)
    return out


def _link_figure(df: Finding, mf: Finding, link: Link, evidence_dir: Path) -> str | None:
    """Pattern or mask beside the flagged crop, written as a real PNG.

    Uses our own writer rather than PIL: a 64x32 pair of images does not justify
    an image dependency in core, and a placeholder is better than a missing file
    the report would render as a broken image.
    """
    from cvassure.core.imaging import NAVY, side_by_side, solid

    dh, mh = df.link_hints, mf.link_hints
    left_path = _evidence_path(evidence_dir, dh.patch_template_path if dh else None)
    right_rel = None
    if mh:
        right_rel = mh.trigger.mask_path or mh.trigger.pattern_path
    right_path = _evidence_path(evidence_dir, right_rel)

    rel = f"evidence/LINK_{mf.id}_{df.id}.png"
    out_png = evidence_dir / f"LINK_{mf.id}_{df.id}.png"

    a = _read_gray(left_path) if left_path else None
    b = _read_gray(right_path) if right_path else None
    if a is not None and b is not None and a.size > 1 and b.size > 1:
        # Resample both onto one grid so the pair is a valid side-by-side.
        h = min(a.shape[0], b.shape[0], 64)
        w = min(a.shape[1], b.shape[1], 64)
        if h >= 2 and w >= 2:
            side_by_side(out_png, _to_rgb(_resample(a, h, w)), _to_rgb(_resample(b, h, w)))
            return rel

    # No usable pair. Still write a labelled placeholder: the report must always
    # have a file to open, and an honest blank beats a broken image icon.
    solid(out_png, 64, 32, NAVY)
    return rel


def _resample(img: np.ndarray, h: int, w: int) -> np.ndarray:
    """Nearest-neighbour resample to (h, w). Numpy only, no decoder needed."""
    g = np.asarray(img, dtype=np.float64)
    if g.ndim == 3:
        g = g.mean(axis=2)
    ys = np.linspace(0, g.shape[0] - 1, h)
    xs = np.linspace(0, g.shape[1] - 1, w)
    return np.array([[g[int(round(y)), int(round(x))] for x in xs] for y in ys], dtype=np.float64)


def _to_rgb(gray: np.ndarray) -> list[list[tuple[int, int, int]]]:
    g = np.asarray(gray, dtype=np.float64)
    if g.ndim == 3:
        g = g.mean(axis=2)
    lo, hi = float(g.min()), float(g.max())
    norm = (g - lo) / (hi - lo) if hi > lo else np.zeros_like(g)
    rgb = (norm * 255).astype(np.uint8)
    return [[(int(v),) * 3 for v in row] for row in rgb]
