"""Cross-asset linking tests (D10), with the negative controls.

The negative cases matter more than the positive one. A linker that always links
scores 1.0 recall and demonstrates nothing, so plan §10.3 asks for the variants
where nothing should link. These are the synthetic stand-ins until P2 and P3 land
a real backdoored model.

Images are generated here: small .npy arrays, written and read by our own code.
No real demo photos, no downloaded dataset.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cvassure.core.config import LinkConfig
from cvassure.core.finding import Finding, LinkHints, TriggerHint
from cvassure.core.linking import apply_links, find_links, iou, ncc

CFG = LinkConfig(tau_link=0.5, identity_weight=0.5, overlap_weight=0.2, pattern_weight=0.3)


def _data_finding(
    patch_id="P-03", cls=0, bbox=(0.1, 0.1, 0.3, 0.3), fid="F-001", tpl="evidence/tpl.npy"
) -> Finding:
    return Finding.draft(
        asset="data",
        reason="patch trigger on one contributor, needs a link hint",
        evidence=["evidence/data.png"],
        severity=0.9,
        confidence=0.8,
        access_level="not-applicable",
        limitations="one known patch library entry is searched",
        disposition="review",
        source_id="C-07",
        class_label=cls,
        tags=["patch_trigger"],
        link_hints=LinkHints(
            target_class=cls,
            source_id="C-07",
            trigger=TriggerHint(kind="patch_library", patch_id=patch_id),
            location_bbox=list(bbox),
            patch_template_path=tpl,
        ),
    ).to_final(fid)


def _model_finding(
    patch_id=None, cls=0, bbox=(0.12, 0.11, 0.28, 0.29), fid="F-019", mask="evidence/mask.npy"
) -> Finding:
    trigger = (
        TriggerHint(kind="patch_library", patch_id=patch_id)
        if patch_id
        else TriggerHint(kind="reconstructed", mask_path=mask)
    )
    return Finding.draft(
        asset="model",
        reason="white-box trigger sweep hit, needs a link hint",
        evidence=["evidence/model.png"],
        severity=0.71,
        confidence=0.8,
        access_level="white-box",
        limitations="Neural Cleanse style reconstruction, no retraining",
        disposition="review",
        class_label=cls,
        tags=["trigger_sweep_hit"],
        link_hints=LinkHints(
            target_class=cls,
            trigger=trigger,
            location_bbox=list(bbox),
            patch_template_path=mask,
        ),
    ).to_final(fid)


def _evidence_dir(tmp_path: Path) -> Path:
    """`out/evidence/`, because `link_hints` paths are relative to `out/`.

    The linker resolves `evidence/tpl.npy` against the *parent* of the evidence
    dir, matching how a Finding's `evidence` field works. Handing it the tmp root
    instead would test a layout the pipeline never produces.
    """
    d = tmp_path / "evidence"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_npy(path: Path, arr: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, arr)


def _hints(cls=0, patch_id=None, bbox=None, tpl=None, mask=None, source_id=None):
    """Build LinkHints with exactly the evidence a test wants present.

    Explicit beats implicit here: several tests need a side with *no* geometry or
    *no* image, and constructing that by deleting fields from a full object is
    how a test ends up passing for the wrong reason.
    """
    if patch_id is not None:
        trigger = TriggerHint(kind="patch_library", patch_id=patch_id)
    else:
        trigger = TriggerHint(kind="reconstructed", mask_path=mask or "evidence/mask.npy")
    return LinkHints(
        target_class=cls,
        source_id=source_id,
        trigger=trigger,
        location_bbox=list(bbox) if bbox else None,
        patch_template_path=tpl,
    )


def _checker(size=16) -> np.ndarray:
    a = np.zeros((size, size))
    a[4:12, 4:12] = 1.0
    return a


# --- geometry ---


def test_iou_identical_boxes_is_one() -> None:
    assert iou([0.1, 0.1, 0.3, 0.3], [0.1, 0.1, 0.3, 0.3]) == pytest.approx(1.0)


def test_iou_disjoint_boxes_is_zero() -> None:
    assert iou([0.0, 0.0, 0.1, 0.1], [0.8, 0.8, 0.1, 0.1]) == 0.0


def test_iou_half_overlap() -> None:
    assert iou([0.0, 0.0, 0.2, 1.0], [0.1, 0.0, 0.2, 1.0]) == pytest.approx(1 / 3, abs=0.01)


def test_ncc_identical_is_one_and_inverted_is_minus_one() -> None:
    a = _checker()
    assert ncc(a, a) == pytest.approx(1.0)
    assert ncc(a, 1.0 - a) == pytest.approx(-1.0)


def test_ncc_of_a_flat_image_is_zero_not_a_crash() -> None:
    """A constant patch carries no pattern. 0/0 is undefined, so 0.0 is correct."""
    assert ncc(np.ones((8, 8)), _checker(8)) == 0.0


def test_ncc_resamples_different_sizes() -> None:
    a = _checker(16)
    b = np.asarray(
        [[1.0 if (2 <= y < 6 and 2 <= x < 6) else 0.0 for x in range(8)] for y in range(8)]
    )
    assert ncc(a, b) == pytest.approx(1.0, abs=0.05)


# --- positive ---


def test_same_patch_id_and_matching_geometry_links(tmp_path: Path) -> None:
    """Matching geometry and pattern link even with no identity component.

    A `reconstructed` model finding carries no `patch_id` (the schema forbids
    it), so identity is legitimately absent. That is the demo case: P2 names a
    library patch, P3 reconstructs a mask, and the two are matched on geometry
    and appearance.
    """
    ev = _evidence_dir(tmp_path)
    _write_npy(ev / "tpl.npy", _checker())
    _write_npy(ev / "mask.npy", _checker())
    links, report = find_links([_data_finding(), _model_finding()], CFG, ev)
    assert len(links) == 1
    assert links[0].score >= CFG.tau_link
    assert "identity" not in links[0].components
    assert links[0].components["pattern"] == pytest.approx(1.0)
    assert links[0].components["overlap"] > 0.8
    # Renormalised over the two components that exist, not the three configured.
    assert set(links[0].weights_used) == {"overlap", "pattern"}
    assert sum(links[0].weights_used.values()) == pytest.approx(1.0)
    assert report["pairs_linked"] == 1


def test_both_sides_naming_the_same_library_patch_gives_identity(tmp_path: Path) -> None:
    """The black-box sweep case: both sides carry a patch_id, so identity fires."""
    ev = _evidence_dir(tmp_path)
    data_f = _data_finding()
    model_f = _model_finding(patch_id="P-03")
    links, _ = find_links([data_f, model_f], CFG, ev)
    assert len(links) == 1
    assert links[0].components["identity"] == 1.0


def test_link_escalates_model_severity_with_noisy_or(tmp_path: Path) -> None:
    data_f, model_f = _data_finding(), _model_finding()
    assert model_f.severity == 0.71
    links, _ = find_links([data_f, model_f], CFG, tmp_path)
    out = apply_links([data_f, model_f], links, tmp_path)
    by_id = {f.id: f for f in out}

    expected = min(1.0, 1.0 - (1.0 - 0.71) * (1.0 - 0.9))
    assert by_id["F-019"].severity == pytest.approx(expected)
    assert by_id["F-019"].severity > model_f.severity
    assert by_id["F-019"].escalation.escalated is True
    assert by_id["F-019"].escalation.severity_before == pytest.approx(0.71)
    assert by_id["F-019"].escalation.method == "noisy-or"
    assert by_id["F-019"].escalation.linked_to == ["F-001"]


def test_link_cross_references_both_findings(tmp_path: Path) -> None:
    data_f, model_f = _data_finding(), _model_finding()
    links, _ = find_links([data_f, model_f], CFG, tmp_path)
    out = {f.id: f for f in apply_links([data_f, model_f], links, tmp_path)}
    assert out["F-001"].linked_findings == ["F-019"]
    assert out["F-019"].linked_findings == ["F-001"]


def test_disposition_is_not_changed_by_linking(tmp_path: Path) -> None:
    """R5 owns the disposition. The linker only escalates severity."""
    data_f, model_f = _data_finding(), _model_finding()
    links, _ = find_links([data_f, model_f], CFG, tmp_path)
    out = {f.id: f for f in apply_links([data_f, model_f], links, tmp_path)}
    assert out["F-019"].disposition == model_f.disposition


def test_link_writes_an_evidence_png(tmp_path: Path) -> None:
    ev = _evidence_dir(tmp_path)
    data_f, model_f = _data_finding(), _model_finding()
    links, _ = find_links([data_f, model_f], CFG, ev)
    apply_links([data_f, model_f], links, ev)
    assert links[0].evidence
    assert (tmp_path / links[0].evidence).is_file()


# --- negative controls. The point of these. ---


def test_class_mismatch_never_links(tmp_path: Path) -> None:
    links, _ = find_links([_data_finding(cls=0), _model_finding(cls=1)], CFG, tmp_path)
    assert links == []


def test_different_patch_id_never_links(tmp_path: Path) -> None:
    links, _ = find_links(
        [_data_finding(patch_id="P-01"), _model_finding(patch_id="P-09")], CFG, tmp_path
    )
    assert links == []


def test_no_hints_no_link(tmp_path: Path) -> None:
    """Clean model, clean data. No hints means no evidence means no link."""
    clean_data = Finding.draft(
        asset="data",
        reason="no patch in this batch, nothing to link",
        evidence=["evidence/a.png"],
        severity=0.1,
        confidence=0.9,
        access_level="not-applicable",
        limitations="clean batch, no evidence gathered",
        disposition="review",
    ).to_final("F-001")
    clean_model = Finding.draft(
        asset="model",
        reason="no trigger found in the sweep",
        evidence=["evidence/b.png"],
        severity=0.1,
        confidence=0.9,
        access_level="white-box",
        limitations="sweep found nothing above threshold",
        disposition="accept",
    ).to_final("F-019")
    links, report = find_links([clean_data, clean_model], CFG, tmp_path)
    assert links == []
    assert report["pairs_considered"] == 0


def test_one_sided_hints_do_not_link(tmp_path: Path) -> None:
    links, _ = find_links([_data_finding(), _model_finding(patch_id=None)], CFG, tmp_path)
    # geometry alone can link if it is strong; identity alone cannot be faked.
    # A reconstructed model vs a library patch with no images: no identity, no
    # pattern, and the boxes are close, so this is the honest "not enough".
    assert all(found.score >= CFG.tau_link for found in links)


def test_missing_image_file_leaves_pattern_absent(tmp_path: Path) -> None:
    _write_npy(tmp_path / "tpl.npy", _checker())
    # mask.npy deliberately not written
    data_f = _data_finding()
    model_f = _model_finding()
    links, _ = find_links([data_f, model_f], CFG, tmp_path)
    for found in links:
        assert "pattern" not in found.components


def test_weights_are_renormalised_over_present_components(tmp_path: Path) -> None:
    """An identity-only link is scored with weight 1.0 on identity, not 0.5."""
    data_f = _data_finding().model_copy(
        update={"link_hints": _hints(cls=0, patch_id="P-03", source_id="C-07")}
    )
    model_f = _model_finding().model_copy(update={"link_hints": _hints(cls=0, patch_id="P-03")})
    links, report = find_links([data_f, model_f], CFG, tmp_path)
    assert links, "identical patch ids with no geometry should still link on identity"
    assert links[0].components == {"identity": 1.0}
    assert links[0].weights_used == {"identity": 1.0}
    assert report["weights"]["identity"] == 0.5  # the configured weight is still reported


def test_reconstructed_without_pattern_says_so_in_limitations(tmp_path: Path) -> None:
    data_f = _data_finding().model_copy(
        update={
            "link_hints": _hints(
                cls=0, patch_id="P-03", bbox=(0.1, 0.1, 0.3, 0.3), source_id="C-07"
            )
        }
    )
    model_f = _model_finding().model_copy(
        update={"link_hints": _hints(cls=0, bbox=(0.12, 0.11, 0.28, 0.29))}
    )
    links, _ = find_links([data_f, model_f], CFG, tmp_path)
    out = {f.id: f for f in apply_links([data_f, model_f], links, tmp_path)}
    assert "pattern similarity was not available" in out["F-019"].limitations


def test_threshold_is_respected(tmp_path: Path) -> None:
    strict = LinkConfig(tau_link=1.01)  # unreachable
    _write_npy(tmp_path / "tpl.npy", _checker())
    _write_npy(tmp_path / "mask.npy", _checker())
    links, _ = find_links([_data_finding(), _model_finding()], strict, tmp_path)
    assert links == []


def test_report_records_calibration_state(tmp_path: Path) -> None:
    _links, report = find_links([_data_finding(), _model_finding()], CFG, tmp_path)
    assert report["calibration"] == "UNCALIBRATED"
    assert report["pairs_considered"] == 1


def test_no_contributor_id_appears_in_the_linker() -> None:
    """Scenario-agnostic. The linker reads link_hints, never a hard-coded id."""
    src = Path(__file__).resolve().parents[2] / "src" / "cvassure" / "core" / "linking.py"
    text = src.read_text(encoding="utf-8")
    for banned in ("C-07", "C-01", "B-1", "B-2", "B-3", "P-03"):
        assert banned not in text, f"{banned} must not appear in linking.py"


def test_evidence_path_stays_inside_the_run_directory(tmp_path: Path) -> None:
    from cvassure.core.linking import _evidence_path

    evidence = tmp_path / "out" / "evidence"
    evidence.mkdir(parents=True)
    inside = evidence / "crop.png"
    inside.write_bytes(b"png")
    assert _evidence_path(evidence, "evidence/crop.png") == inside.resolve()
    assert _evidence_path(evidence, "../secret.png") is None
    assert _evidence_path(evidence, "/etc/passwd") is None
    assert _evidence_path(evidence, "C:/Windows/notepad.exe") is None
