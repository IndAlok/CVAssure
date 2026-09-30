"""Detector contract.

A detector is a class with class attributes and a `run` method. It returns a
`DetectorResult` of Findings. It does not return dicts, it does not open sockets,
it does not write outside `ctx.out_dir`, and it does not read a ground-truth
attack manifest.

The pipeline enforces two rules before and around `run`.

An exception in `run` becomes one `asset=system` Finding that names the detector,
and the run continues.

If `requires` is not a subset of the wrapper capabilities, the pipeline marks the
detector `skipped` and does not call `run`. A missing wrapper is the same skip.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover - import cycle guard, runtime_checkable keeps it lazy
    from cvassure.core.audit import ChainBackend
    from cvassure.core.finding import Finding

DetectorStatus = Literal["ok", "skipped", "error"]

#: Access tiers, ordered from most to least. The model wrapper declares one.
AccessTier = Literal["white-box", "gray-box", "black-box", "not-applicable"]

#: Wrapper capabilities a detector may name in ``requires``.
Capability = Literal["weights", "gradients", "activations", "logits", "query_only"]


@runtime_checkable
class ModelWrapper(Protocol):
    """Methods the pipeline reads from a model wrapper."""

    def declare_access_tier(self) -> AccessTier: ...

    def capabilities(self) -> frozenset[Capability]: ...

    def weight_digest(self) -> str: ...


@dataclass(frozen=True)
class Sample:
    """One row of the internal sample table."""

    sample_id: str
    path: Path
    class_id: int | str | None = None
    source_id: str | None = None
    batch_id: str | None = None


@dataclass(frozen=True)
class Dataset:
    """Handle the adapters hand to detectors. Read-only by construction."""

    root: Path
    format: str
    samples: tuple[Sample, ...]
    #: Contributor and batch come from extra annotation fields or a sidecar JSON.
    #: Never from the ground-truth attack manifest.
    sidecar: Mapping[str, Any] = field(default_factory=dict)

    def by_source(self, source_id: str) -> tuple[Sample, ...]:
        return tuple(s for s in self.samples if s.source_id == source_id)

    def sources(self) -> tuple[str, ...]:
        return tuple(sorted({s.source_id for s in self.samples if s.source_id}))


@dataclass(frozen=True)
class AuditContext:
    """Read-only input to a detector. It has no attribute for the manifest.

    If your method needs ground truth to work, it is an evaluation script, not a
    detector. Move it under ``scripts/``.
    """

    seed: int
    out_dir: Path
    evidence_dir: Path
    cache_dir: Path
    config: Mapping[str, Any]
    dataset: Dataset | None = None
    model: ModelWrapper | None = None
    records_path: Path | None = None
    pubkey_path: Path | None = None
    logger: Any = None
    audit: ChainBackend | None = None
    prior_findings: tuple[Finding, ...] = ()

    def stage_out(self, *parts: str) -> Path:
        """A path under out_dir. Detectors write nowhere else."""
        p = self.out_dir.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


@dataclass
class DetectorResult:
    """What ``run`` returns. Findings in, no side channels out."""

    status: DetectorStatus = "ok"
    findings: list[Finding] = field(default_factory=list)
    #: Numbers for the run manifest. Keys are detector-local.
    metrics: dict[str, Any] = field(default_factory=dict)
    #: The right-hand text on the CLI line for this stage. One line, no newlines.
    summary: str = ""
    #: Paths written under out_dir, relative to out_dir.
    artifacts: list[str] = field(default_factory=list)
    #: Extra honesty text folded into the coverage statement.
    limitations: list[str] = field(default_factory=list)
    skipped_reason: str | None = None
    runtime_s: float | None = None


class Detector(ABC):
    """Subclass this. Four class attributes and one method."""

    #: Stable, dotted, unique across the registry. Real module wins over a stub.
    id: ClassVar[str]
    #: One of data | model | records | shift. Determines pipeline stage order.
    asset: ClassVar[str]
    #: Package or component name, for example "data" or "model".
    owner: ClassVar[str]
    version: ClassVar[str]
    #: Wrapper capabilities needed. Empty means "works on any tier".
    requires: ClassVar[frozenset[str]] = frozenset()

    def configure(self, cfg: Mapping[str, Any]) -> None:  # noqa: B027 - optional hook, see docstring
        """Optional. Called once before ``run``. Keep per-detector config here.

        Intentionally concrete and empty: making it abstract would force every
        data detector to write a no-op method, and giving it a body here would
        hide the fact that per-detector config is the override's job.
        """

    @abstractmethod
    def run(self, ctx: AuditContext) -> DetectorResult:
        """Do the work. Deterministic given ``ctx.seed``.

        Return Findings, do not raise for a bad input file: a caught error with
        an honest reason beats a stack trace. Raising is fine too, the pipeline
        isolates you and records it.
        """

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Detector {self.id} v{self.version} owner={self.owner}>"


def interface_errors(det: object) -> list[str]:
    """Registry check. Returns a list of contract violations, empty when fine.

    Kept next to the contract so tests can call it without importing the registry.
    """
    problems: list[str] = []
    for attr in ("id", "version", "owner"):
        if not isinstance(getattr(det, attr, None), str) or not getattr(det, attr):
            problems.append(f"{attr} must be a non-empty ClassVar[str]")
    if getattr(det, "asset", None) not in ("data", "model", "records", "shift"):
        problems.append(f"asset {getattr(det, 'asset', None)!r} is not data|model|records|shift")
    if not isinstance(getattr(det, "requires", None), frozenset):
        problems.append("requires must be a frozenset")
    if not callable(getattr(det, "run", None)):
        problems.append("run must be callable")
    return problems
