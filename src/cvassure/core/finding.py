"""The object every detector emits.

`additionalProperties` is false at the top level. Unknown keys fail validation.
Detector-specific numbers go in `metadata`.

`severity` is impact if the finding is true. `confidence` is belief that it is
true. They are separate fields.

`limitations` is required and non-empty. `disposition` is written by the policy
engine. A detector may propose one. Policy overwrites it before write-out.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from functools import lru_cache
from typing import Any, Literal

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

SCHEMA_VERSION = "1.0"
ID_PATTERN = r"^F-\d{3,}$"

Asset = Literal["data", "model", "records", "shift", "system"]
Disposition = Literal["accept", "review", "quarantine", "rejected"]
AccessLevel = Literal["white-box", "gray-box", "black-box", "not-applicable"]
TriggerKind = Literal["patch_library", "reconstructed"]

#: The only words allowed in ``tags``. Adding one is a schema-version discussion.
TAG_VOCABULARY: tuple[str, ...] = (
    "patch_trigger",
    "blend_trigger",
    "label_flip",
    "near_duplicate",
    "ood",
    "fingerprint_mismatch",
    "weight_digest_mismatch",
    "trigger_sweep_hit",
    "trigger_reconstructed",
    "verification_failed",
    "replay",
    "substitution",
    "drift",
    "manipulation",
    "undetermined",
    "skipped_access_tier",
)
Tag = Literal[
    "patch_trigger",
    "blend_trigger",
    "label_flip",
    "near_duplicate",
    "ood",
    "fingerprint_mismatch",
    "weight_digest_mismatch",
    "trigger_sweep_hit",
    "trigger_reconstructed",
    "verification_failed",
    "replay",
    "substitution",
    "drift",
    "manipulation",
    "undetermined",
    "skipped_access_tier",
]

#: Tag pairs that force a ``link_hints`` block. The cross-asset linker needs
#: geometric evidence, not just a verdict.
LINK_HINT_REQUIRED_TAGS: frozenset[str] = frozenset(
    {"patch_trigger", "blend_trigger", "trigger_sweep_hit", "trigger_reconstructed"}
)

MAX_SAMPLE_IDS = 50
MAX_REASON = 300
MIN_REASON = 10
MIN_LIMITATIONS = 10
MAX_LINKS = 50  # linked_findings cap. A finding that links to everything links to nothing.

REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "id",
    "asset",
    "reason",
    "evidence",
    "severity",
    "confidence",
    "access_level",
    "limitations",
    "disposition",
    "linked_findings",
)


class DetectorRef(BaseModel):
    """Who produced this. The pipeline fills it. Detectors do not."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    owner: str = Field(min_length=1)


class TriggerHint(BaseModel):
    """Which visual trigger a finding is about.

    ``patch_library`` hints carry a ``patch_id`` from a known patch set.
    ``reconstructed`` hints carry a mask, and optionally a pattern image.
    """

    model_config = ConfigDict(extra="forbid")
    kind: TriggerKind
    patch_id: str | None = Field(default=None, min_length=1)
    mask_path: str | None = None
    pattern_path: str | None = None

    @model_validator(mode="after")
    def _kind_matches_payload(self) -> TriggerHint:
        if self.kind == "patch_library" and not self.patch_id:
            raise ValueError("patch_library trigger requires patch_id")
        if self.kind == "reconstructed" and not self.mask_path:
            raise ValueError("reconstructed trigger requires mask_path")
        if self.kind == "reconstructed" and self.patch_id:
            raise ValueError(
                "reconstructed trigger has no patch_id. That would fake an identity match"
            )
        return self


class LinkHints(BaseModel):
    """Evidence the cross-asset linker reads. Not a verdict.

    Data findings tagged `patch_trigger` or `blend_trigger` carry this.
    Model findings tagged `trigger_sweep_hit` or `trigger_reconstructed` carry it.
    """

    model_config = ConfigDict(extra="forbid")
    target_class: int | str | None = None
    source_id: str | None = Field(default=None, min_length=1)
    trigger: TriggerHint
    #: [x, y, w, h] normalised to 0-1, image coordinates, origin top-left.
    location_bbox: list[float] | None = None
    patch_template_path: str | None = None

    @field_validator("location_bbox")
    @classmethod
    def _bbox_shape(cls, v: list[float] | None) -> list[float] | None:
        if v is None:
            return v
        if len(v) != 4:
            raise ValueError("location_bbox must be [x, y, w, h]")
        if any(c < 0.0 or c > 1.0 for c in v):
            raise ValueError("location_bbox values must be normalised to 0-1")
        if v[2] <= 0.0 or v[3] <= 0.0:
            raise ValueError("location_bbox width and height must be positive")
        return v


class Escalation(BaseModel):
    """Written by the linker only. Records what the severity was before."""

    model_config = ConfigDict(extra="forbid")
    escalated: bool
    severity_before: float = Field(ge=0.0, le=1.0)
    linked_to: list[str] = Field(default_factory=list)
    method: str = Field(min_length=1)


class PolicyRef(BaseModel):
    """Which rule decided the disposition. Written by the policy engine only."""

    model_config = ConfigDict(extra="forbid")
    rule_id: str = Field(min_length=1)
    policy_hash: str = Field(min_length=1, pattern=r"^[0-9a-f]{64}$")


class Finding(BaseModel):
    """One assurance flag."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    #: Pipeline-assigned. Absent on drafts, so ``draft()`` rejects it.
    id: str | None = Field(default=None, pattern=ID_PATTERN)
    asset: Asset
    reason: str = Field(min_length=MIN_REASON, max_length=MAX_REASON)
    #: Relative paths under out/evidence/. Absolute paths and ``..`` are rejected.
    evidence: list[str] = Field(default_factory=list)
    severity: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    access_level: AccessLevel
    limitations: str = Field(min_length=MIN_LIMITATIONS)
    disposition: Disposition
    linked_findings: list[str] = Field(default_factory=list, max_length=MAX_LINKS)

    detector: DetectorRef | None = None
    source_id: str | None = Field(default=None, min_length=1)
    batch_id: str | None = Field(default=None, min_length=1)
    class_label: int | str | None = None
    sample_ids: list[str] = Field(default_factory=list, max_length=MAX_SAMPLE_IDS)
    sample_count: int | None = Field(default=None, ge=0)
    tags: list[Tag] = Field(default_factory=list)
    link_hints: LinkHints | None = None
    escalation: Escalation | None = None
    policy: PolicyRef | None = None
    stub: bool = False
    #: Free JSON. The only place an unknown key is allowed.
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def draft(cls, **fields: Any) -> Finding:
        """Build a finding without an id. The pipeline assigns ids and sorts."""
        if "id" in fields:
            raise TypeError("draft findings carry no id. The pipeline assigns it")
        return cls(**fields)

    def to_final(self, finding_id: str) -> Finding:
        """Re-validate with the pipeline-assigned id, rejecting a bad one here."""
        return type(self).model_validate({**self.model_dump(), "id": finding_id})

    def with_detector(self, detector_id: str, version: str, owner: str) -> Finding:
        """Stamp who produced this. The pipeline owns the field. Detectors do not.

        Goes through ``model_copy`` with a real ``DetectorRef`` rather than plain
        attribute assignment, which would leave a raw dict in a typed field and
        blow up later at ``f.detector.id``.
        """
        return self.model_copy(
            update={"detector": DetectorRef(id=detector_id, version=version, owner=owner)}
        )

    @field_validator("reason")
    @classmethod
    def _one_line(cls, v: str) -> str:
        if "\n" in v or "\r" in v:
            raise ValueError("reason is one line. Put detail in metadata or limitations")
        return v

    @field_validator("evidence")
    @classmethod
    def _relative_evidence(cls, paths: list[str]) -> list[str]:
        for p in paths:
            if not p:
                raise ValueError("empty evidence path")
            if "\\" in p:
                raise ValueError("evidence path must use forward slashes")
            if p.startswith("/") or p.startswith("~"):
                raise ValueError(f"evidence path must be relative, got {p!r}")
            if len(p) > 1 and p[1] == ":":
                raise ValueError(f"evidence path must be relative, got drive-lettered {p!r}")
            parts = p.split("/")
            if ".." in parts:
                raise ValueError(f"evidence path must not traverse upwards, got {p!r}")
        return paths

    @field_validator("linked_findings")
    @classmethod
    def _link_ids(cls, ids: list[str]) -> list[str]:
        for i in ids:
            if not re.match(ID_PATTERN, i):
                raise ValueError(f"linked_findings entry {i!r} is not a finding id")
        return ids

    @model_validator(mode="after")
    def _cross_field_rules(self) -> Finding:
        # Evidence may only be empty when the error itself is the evidence.
        if not self.evidence and self.asset != "system":
            raise ValueError("only asset=system may have empty evidence")

        for t in self.tags:
            if t not in TAG_VOCABULARY:
                raise ValueError(f"{t!r} is not in the tag vocabulary")

        if self.tags and LINK_HINT_REQUIRED_TAGS.intersection(self.tags) and not self.link_hints:
            raise ValueError(
                "a finding tagged "
                f"{sorted(LINK_HINT_REQUIRED_TAGS.intersection(self.tags))} "
                "must carry link_hints. The linker needs geometry, not a verdict"
            )

        if self.link_hints and self.link_hints.source_id and self.asset != "data":
            raise ValueError("link_hints.source_id is only meaningful on a data finding")
        if self.link_hints and not self.tags:
            raise ValueError("link_hints without a tag loses the reason for the link")

        if self.metadata:
            for k in self.metadata:
                if not isinstance(k, str):
                    raise ValueError("metadata keys must be strings")

        return self


def _base_schema() -> dict[str, Any]:
    return Finding.model_json_schema(mode="validation")


def final_schema() -> dict[str, Any]:
    """JSON Schema 2020-12 for a finding the pipeline has finished with."""
    s = _base_schema()
    s["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    s["$id"] = "https://cvassure.local/contracts/finding.schema.json"
    s["title"] = "CVAssure Finding"
    s["description"] = (
        "One assurance flag. Detector-proposed fields are filled by the pipeline."
    )
    s["properties"]["id"] = {"type": "string", "pattern": ID_PATTERN}
    s["required"] = list(REQUIRED_FIELDS)
    return s


def draft_schema() -> dict[str, Any]:
    """Same contract minus ``id``, for what a detector hands in."""
    s = final_schema()
    s["$id"] = "https://cvassure.local/contracts/finding.draft.schema.json"
    s["title"] = "CVAssure Finding (draft)"
    s["properties"].pop("id", None)
    s["required"] = [f for f in REQUIRED_FIELDS if f != "id"]
    return s


def is_finite_unit(v: float) -> bool:
    """Severity/confidence guard. Also the reason ``allow_inf_nan=False`` exists."""
    return math.isfinite(v) and 0.0 <= v <= 1.0


@lru_cache(maxsize=1)
def _final_validator() -> Draft202012Validator:
    v = Draft202012Validator(final_schema())
    v.check_schema(final_schema())
    return v


class SchemaError(ValueError):
    """A finding that must not reach the linker or the report. Names the detector."""

    def __init__(self, message: str, *, detector_id: str | None = None) -> None:
        self.detector_id = detector_id
        super().__init__(f"{detector_id}: {message}" if detector_id else message)


def validate_finding(doc: Mapping[str, Any], *, detector_id: str | None = None) -> Finding:
    """The pipeline's gate. JSON Schema first, then the pydantic cross-field rules.

    Both, always. JSON Schema 2020-12 checks types, enums, patterns and closed
    property sets, and it is what external consumers can rely on. It cannot
    express "only asset=system may have empty evidence" or "NaN is not a number",
    so pydantic runs second and owns those. Neither alone is the contract.

    Raises :class:`SchemaError` so the CLI can exit 3 naming the guilty detector.
    """
    try:
        _final_validator().validate(dict(doc))
    except JsonSchemaError as exc:
        where = "/".join(str(p) for p in exc.absolute_path) or "<root>"
        raise SchemaError(f"{where}: {exc.message}", detector_id=detector_id) from exc
    try:
        return Finding.model_validate(dict(doc))
    except ValidationError as exc:
        raise SchemaError(str(exc), detector_id=detector_id) from exc
