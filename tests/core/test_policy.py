"""Policy engine tests (D8). Every rule, precedence, and the security cases.

The policy file is untrusted input in the demo: a judge may edit it in front of
us. These tests are the reason that is safe.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cvassure.core.config import ConfigError, load_yaml
from cvassure.core.finding import Finding, LinkHints, TriggerHint
from cvassure.core.policy import PolicyError, apply_policy, load_policy

REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / "policies" / "default.yaml"


def _f(**kw) -> Finding:
    base = {
        "asset": "data",
        "reason": "a sufficiently long reason string",
        "evidence": ["evidence/x.png"],
        "severity": 0.5,
        "confidence": 0.5,
        "access_level": "not-applicable",
        "limitations": "a limitation long enough to pass",
        "disposition": "review",
    }
    base.update(kw)
    return Finding.draft(**base)


def test_default_policy_matches_the_published_schema() -> None:
    import json

    from jsonschema import Draft202012Validator

    schema = json.loads(
        (Path(__file__).resolve().parents[2] / "contracts" / "policy.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(load_yaml(DEFAULT))


def test_extra_top_level_key_is_rejected(tmp_path: Path) -> None:
    p = tmp_path / "extra.yaml"
    p.write_text("version: 1\nname: t\nrules: []\nnote: no\n", encoding="utf-8")
    with pytest.raises(PolicyError):
        load_policy(p)


def test_default_policy_loads_and_hashes() -> None:
    p = load_policy(DEFAULT)
    assert p.name == "cvassure-default"
    assert p.version == 1
    assert len(p.policy_hash) == 64
    assert {r.id for r in p.rules} >= {
        "R1-quarantine-high-data",
        "R2-review-model",
        "R3-reject-bad-records",
        "R4-quarantine-manipulation",
        "R5-review-linked-model",
    }


@pytest.mark.parametrize(
    ("finding", "expected", "rule"),
    [
        (_f(asset="data", severity=0.9, confidence=0.7), "quarantine", "R1-quarantine-high-data"),
        (_f(asset="data", severity=0.85, confidence=0.5), "review", "default"),
        (_f(asset="model", severity=0.6), "review", "R2-review-model"),
        (_f(asset="model", severity=0.2), "review", "default"),
        (_f(asset="records", tags=["verification_failed"]), "rejected", "R3-reject-bad-records"),
        (
            _f(asset="records", tags=["replay", "verification_failed"]),
            "rejected",
            "R3-reject-bad-records",
        ),
        (
            _f(asset="shift", batch_id="B-3", tags=["manipulation"]),
            "quarantine",
            "R4-quarantine-manipulation",
        ),
        (_f(asset="shift", batch_id="B-2", tags=["drift"]), "review", "default"),
        (_f(asset="system", evidence=[]), "review", "R6-review-system"),
    ],
)
def test_each_rule_fires(finding, expected, rule) -> None:
    policy = load_policy(DEFAULT)
    disp, rid, _ = policy.apply(finding.to_final("F-001"))
    assert (disp, rid) == (expected, rule)


def test_no_matching_rule_gives_review_never_accept() -> None:
    """A finding no rule matches must not look clean. review, not accept."""
    policy = load_policy(DEFAULT)
    # asset=records with a tag no rule keys on, and a severity below R2's floor.
    f = _f(asset="records", tags=["drift"], severity=0.2).to_final("F-001")
    disp, rid, _ = policy.apply(f)
    assert (disp, rid) == ("review", "default")


def test_a_matching_rule_is_always_recorded_even_if_same_as_default() -> None:
    """R2 produces `review`, the same as the default. The report must still say R2.

    Blurring "the policy decided this" into "the policy said nothing" is how a
    reviewer stops being able to audit a disposition.
    """
    policy = load_policy(DEFAULT)
    disp, rid, _ = policy.apply(_f(asset="model", severity=0.6).to_final("F-001"))
    assert (disp, rid) == ("review", "R2-review-model")


def test_precedence_beats_rule_order(tmp_path: Path) -> None:
    """Reordering rules cannot change an outcome. That is what makes it reviewable."""
    a = tmp_path / "a.yaml"
    a.write_text(
        "version: 1\nname: t\nprecedence: [rejected, quarantine, review, accept]\n"
        "rules:\n"
        "  - {id: review-first, when: {asset: data}, then: {disposition: review}}\n"
        "  - {id: quar-second, when: {asset: data}, then: {disposition: quarantine}}\n",
        encoding="utf-8",
    )
    b = tmp_path / "b.yaml"
    b.write_text(
        a.read_text(encoding="utf-8")
        .replace("review-first", "quar-first")
        .replace("quar-second", "review-second"),
        encoding="utf-8",
    )
    f = _f(asset="data").to_final("F-001")
    assert load_policy(a).apply(f)[0] == load_policy(b).apply(f)[0] == "quarantine"


def test_r5_fires_when_a_linked_neighbour_is_quarantined() -> None:
    """The demo's model disposition. A link to a quarantined source means review.

    Exercised through `apply_policy`, not `Policy.apply` directly, because R5 asks
    about the neighbour's disposition and that only exists once pass one has
    resolved it. Calling `Policy.apply` with a still-undispositioned neighbour
    would test a path the pipeline never takes.
    """
    policy = load_policy(DEFAULT)
    data_f = _f(
        asset="data", severity=0.9, confidence=0.9, source_id="C-07", batch_id=None
    ).to_final("F-001")
    model_f = _f(asset="model", severity=0.7).to_final("F-002")
    model_f = model_f.model_copy(update={"linked_findings": ["F-001"]})

    out, hits = apply_policy([data_f, model_f], policy)
    by_id = {f.id: f for f in out}
    # R1 quarantines the data side. R5 then reviews the model that links to it.
    assert by_id["F-001"].disposition == "quarantine"
    assert by_id["F-001"].policy.rule_id == "R1-quarantine-high-data"
    assert by_id["F-002"].disposition == "review"
    assert by_id["F-002"].policy.rule_id == "R5-review-linked-model"
    assert hits["R5-review-linked-model"] == 1


def test_r5_does_not_fire_without_a_quarantined_neighbour() -> None:
    """The negative control. A link to a merely-reviewed source is not R5."""
    policy = load_policy(DEFAULT)
    weak = _f(asset="data", severity=0.2).to_final("F-001")
    model_f = _f(asset="model", severity=0.7).to_final("F-002")
    model_f = model_f.model_copy(update={"linked_findings": ["F-001"]})
    out, _ = apply_policy([weak, model_f], policy)
    by_id = {f.id: f for f in out}
    assert by_id["F-001"].disposition == "review"
    assert by_id["F-002"].policy.rule_id == "R2-review-model"


def test_missing_field_in_a_rule_does_not_match() -> None:
    """A finding with no source_id must not satisfy a rule keyed on source_id."""
    policy = load_policy(DEFAULT)
    assert policy.apply(_f(asset="data", severity=0.1).to_final("F-001"))[0] == "review"


def test_apply_policy_writes_the_ref_and_counts_hits() -> None:
    policy = load_policy(DEFAULT)
    fs = [
        _f(asset="data", severity=0.9, confidence=0.9).to_final("F-001"),
        _f(asset="records", tags=["verification_failed"]).to_final("F-002"),
    ]
    out, hits = apply_policy(fs, policy)
    assert all(f.policy is not None for f in out)
    assert all(f.policy.rule_id for f in out)
    assert out[0].policy.policy_hash == policy.policy_hash
    assert hits["R1-quarantine-high-data"] == 1
    assert hits["R3-reject-bad-records"] == 1


def test_policy_overwrites_the_detectors_proposal() -> None:
    """A detector may propose. Policy decides."""
    policy = load_policy(DEFAULT)
    greedy = _f(asset="records", tags=["verification_failed"], disposition="accept").to_final(
        "F-001"
    )
    out, _ = apply_policy([greedy], policy)
    assert out[0].disposition == "rejected"


# --- security: the policy file is untrusted input ---


def test_python_object_tag_fails_closed(tmp_path: Path) -> None:
    p = tmp_path / "evil.yaml"
    p.write_text(
        "version: 1\nname: t\nrules: []\nx: !!python/object/apply:os.system ['echo pwned']\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_yaml(p)


def test_unknown_operator_is_a_config_error_not_a_skip(tmp_path: Path) -> None:
    """A rule that silently does not apply is the most dangerous broken policy."""
    p = tmp_path / "bad.yaml"
    p.write_text(
        "version: 1\nname: t\nrules:\n  - {id: r, when: {severity: {approx: 0.5}},"
        " then: {disposition: review}}\n",
        encoding="utf-8",
    )
    with pytest.raises((PolicyError, ConfigError)):
        load_policy(p)


def test_unknown_field_is_a_config_error(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "version: 1\nname: t\nrules:\n  - {id: r, when: {nonsense: 1},"
        " then: {disposition: review}}\n",
        encoding="utf-8",
    )
    with pytest.raises((PolicyError, ConfigError)):
        load_policy(p)


def test_default_may_not_be_accept(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "version: 1\nname: t\ndefaults: {disposition: accept}\nrules: []\n", encoding="utf-8"
    )
    with pytest.raises((PolicyError, ConfigError)):
        load_policy(p)


def test_bad_disposition_is_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "version: 1\nname: t\nrules:\n  - {id: r, when: {asset: data},"
        " then: {disposition: delete_everything}}\n",
        encoding="utf-8",
    )
    with pytest.raises((PolicyError, ConfigError)):
        load_policy(p)


def test_duplicate_rule_id_is_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "version: 1\nname: t\nrules:\n  - {id: r, when: {asset: data}, then: {}}\n"
        "  - {id: r, when: {asset: model}, then: {}}\n",
        encoding="utf-8",
    )
    with pytest.raises((PolicyError, ConfigError)):
        load_policy(p)


def test_malformed_yaml_fails_closed(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("version: 1\nname: [unclosed\n", encoding="utf-8")
    with pytest.raises((PolicyError, ConfigError)):
        load_policy(p)


def test_no_contributor_id_appears_in_the_default_policy() -> None:
    """The default policy does not name a contributor, batch, or class id."""
    text = DEFAULT.read_text(encoding="utf-8")
    for banned in ("C-07", "C-01", "B-1", "B-2", "B-3"):
        assert banned not in text, f"{banned} must not appear in a policy rule"


def test_contains_operator_on_tags(tmp_path: Path) -> None:
    p = tmp_path / "t.yaml"
    p.write_text(
        "version: 1\nname: t\nrules:\n  - {id: r, when: {tags: {contains: drift}},"
        " then: {disposition: accept}}\n",
        encoding="utf-8",
    )
    policy = load_policy(p)
    assert policy.apply(_f(asset="shift", tags=["drift"]).to_final("F-001"))[0] == "accept"
    assert policy.apply(_f(asset="shift", tags=["manipulation"]).to_final("F-001"))[0] == "review"


def test_link_hints_survive_policy_application() -> None:
    """Linking runs first. Policy must not drop the evidence it needs."""
    hints = LinkHints(
        target_class=0,
        trigger=TriggerHint(kind="patch_library", patch_id="P-03"),
        location_bbox=[0.1, 0.1, 0.3, 0.3],
    )
    f = _f(
        asset="data", severity=0.9, confidence=0.9, tags=["patch_trigger"], link_hints=hints
    ).to_final("F-001")
    out, _ = apply_policy([f], load_policy(DEFAULT))
    assert out[0].link_hints is not None
    assert out[0].link_hints.trigger.patch_id == "P-03"
