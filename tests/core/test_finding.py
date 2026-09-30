"""Finding schema tests (D2).

Valid fixtures are real files: they double as the reference examples in
``contracts/FINDING.md`` and as the mock-up 1C shape. Invalid cases are a
mutation table in the test rather than eight near-identical JSON files, so the
failure reason sits next to the case that causes it.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError as PydanticValidationError

from cvassure.core.finding import (
    TAG_VOCABULARY,
    Finding,
    SchemaError,
    draft_schema,
    final_schema,
    validate_finding,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "findings"
VALID = sorted(FIXTURES.glob("valid_*.json"))


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    v = Draft202012Validator(final_schema())
    v.check_schema(final_schema())
    return v


def test_schemas_are_valid_draft_2020_12() -> None:
    for schema in (final_schema(), draft_schema()):
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False


def test_contract_schemas_on_disk_match_the_model() -> None:
    """The committed JSON is generated, not hand-edited. Drift fails here."""
    root = Path(__file__).resolve().parents[2] / "contracts"
    assert json.loads((root / "finding.schema.json").read_text(encoding="utf-8")) == final_schema()
    assert (
        json.loads((root / "finding.draft.schema.json").read_text(encoding="utf-8"))
        == draft_schema()
    )


def test_at_least_six_valid_fixtures() -> None:
    assert len(VALID) >= 6, f"plan asks for 6+, found {len(VALID)}: {[p.name for p in VALID]}"


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_valid_fixture_passes_both_validators(path: Path, validator: Draft202012Validator) -> None:
    doc = _load(path.name)
    validator.validate(doc)
    Finding.model_validate(doc)  # pydantic enforces what JSON Schema cannot (NaN, cross-field)


def test_valid_fixtures_cover_every_asset() -> None:
    assets = {_load(p.name)["asset"] for p in VALID}
    assert assets == {"data", "model", "records", "shift", "system"}


def test_mockup_1c_linked_pair_validates(validator: Draft202012Validator) -> None:
    """F-019 model, linked to F-012. Mock-up layout, legal numbers, not a result."""
    doc = _load("valid_model_sweep_linked.json")
    validator.validate(doc)
    assert doc["id"] == "F-019"
    assert doc["linked_findings"] == ["F-001"]
    assert doc["escalation"]["escalated"] is True
    assert doc["escalation"]["severity_before"] < doc["severity"]


# --- invalid cases. Each is (name, mutation, expected substring in the error). ---

BASE = _load("valid_data_patch.json")


def _mutate(fn):
    doc = copy.deepcopy(BASE)
    fn(doc)
    return doc


def _nan_severity(d: dict) -> None:
    d["severity"] = float("nan")


INVALID_CASES = [
    ("missing_limitations", lambda d: d.pop("limitations"), "limitations"),
    ("severity_above_one", lambda d: d.update(severity=1.2), "severity"),
    ("nan_severity", _nan_severity, "severity"),
    ("inf_confidence", lambda d: d.update(confidence=float("inf")), "confidence"),
    ("extra_property", lambda d: d.update(subject={"id": "C-07"}), "subject"),
    ("bad_id", lambda d: d.update(id="finding-1"), "id"),
    ("absolute_evidence_path", lambda d: d.update(evidence=["C:/tmp/x.png"]), "evidence"),
    ("traversal_evidence_path", lambda d: d.update(evidence=["../../etc/passwd"]), "evidence"),
    ("empty_reason", lambda d: d.update(reason=""), "reason"),
    ("short_reason", lambda d: d.update(reason="bad"), "reason"),
    ("multiline_reason", lambda d: d.update(reason="line one\nline two padding"), "reason"),
    ("unknown_tag", lambda d: d.update(tags=["definitely_malicious"]), "tag"),
    ("missing_id", lambda d: d.pop("id"), "id"),
    ("empty_evidence_non_system", lambda d: d.update(evidence=[]), "evidence"),
    ("bad_disposition", lambda d: d.update(disposition="delete"), "disposition"),
    ("bad_asset", lambda d: d.update(asset="dataset"), "asset"),
    ("bad_access_level", lambda d: d.update(access_level="root"), "access_level"),
    (
        "too_many_sample_ids",
        lambda d: d.update(sample_ids=[f"s-{i}" for i in range(51)]),
        "sample_ids",
    ),
    ("link_hints_without_geometry", lambda d: d.pop("link_hints"), "link_hints"),
    (
        "reconstructed_with_patch_id",
        lambda d: d["link_hints"].update(
            trigger={"kind": "reconstructed", "patch_id": "P-03", "mask_path": "m.png"}
        ),
        "patch_id",
    ),
    (
        "bbox_out_of_range",
        lambda d: d["link_hints"].update(location_bbox=[0.1, 0.1, 1.4, 0.3]),
        "location_bbox",
    ),
    ("link_hints_on_model", lambda d: d.update(asset="model"), "source_id"),
    (
        "bad_policy_hash",
        lambda d: d.update(policy={"rule_id": "R1", "policy_hash": "abc"}),
        "policy_hash",
    ),
]


@pytest.mark.parametrize(
    ("name", "mutate", "needle"), INVALID_CASES, ids=[c[0] for c in INVALID_CASES]
)
def test_invalid_fixture_is_rejected(name, mutate, needle) -> None:
    """The pipeline's real gate. Both validators, not JSON Schema alone."""
    doc = _mutate(mutate)
    with pytest.raises(SchemaError) as exc:
        validate_finding(doc, detector_id="data.patch_trigger")
    assert needle in str(exc.value), f"{name}: expected {needle!r} in {exc.value}"
    assert "data.patch_trigger" in str(exc.value)


@pytest.mark.parametrize("case", INVALID_CASES, ids=[c[0] for c in INVALID_CASES])
def test_schema_error_names_the_guilty_detector(case) -> None:
    """Exit 3 has to be actionable: the CLI must say which detector broke the contract."""
    _name, mutate, _needle = case
    with pytest.raises(SchemaError) as exc:
        validate_finding(_mutate(mutate), detector_id="model.trigger_sweep")
    assert exc.value.detector_id == "model.trigger_sweep"


def test_draft_rejects_id_but_final_requires_it(validator: Draft202012Validator) -> None:
    draft = draft_schema()
    assert "id" not in draft["properties"]
    assert "id" not in draft["required"]
    assert "id" in validator.schema["required"]


def test_draft_helper_and_id_assignment() -> None:
    f = Finding.draft(
        **{
            k: v
            for k, v in BASE.items()
            if k not in ("id", "detector", "policy", "escalation", "linked_findings")
        }
    )
    assert f.id is None
    with pytest.raises(TypeError, match="carry no id"):
        Finding.draft(**{**BASE, "id": "F-001"})

    final = f.to_final("F-042")
    assert final.id == "F-042"
    with pytest.raises(PydanticValidationError):
        f.to_final("nope")


def test_tag_vocabulary_is_closed() -> None:
    """A new tag is a schema-version discussion, not a one-line addition."""
    with pytest.raises(PydanticValidationError):
        Finding.model_validate({**copy.deepcopy(BASE), "tags": ["brand_new_tag"]})
    assert len(TAG_VOCABULARY) == 16
    assert len(set(TAG_VOCABULARY)) == len(TAG_VOCABULARY)


def test_metadata_is_the_only_free_form_field() -> None:
    f = Finding.model_validate({**copy.deepcopy(BASE), "metadata": {"any": [1, {"nested": True}]}})
    assert f.metadata["any"] == [1, {"nested": True}]
    with pytest.raises(PydanticValidationError):
        Finding.model_validate({**copy.deepcopy(BASE), "extra_top_level": 1})


def test_severity_and_confidence_are_independent_axes() -> None:
    """High severity + low confidence is a valid, useful combination."""
    f = Finding.model_validate({**copy.deepcopy(BASE), "severity": 0.95, "confidence": 0.2})
    assert f.severity == 0.95 and f.confidence == 0.2
