"""Config loading. `yaml.safe_load` or nothing.

No `eval`, no `exec`, no `simpleeval`, anywhere in this file or in the policy
engine. A policy file is untrusted input: it comes from whoever runs the audit,
and in the demo it is a file on disk that a judge may edit in front of us.

A `!!python/object` tag makes PyYAML reach for `object.__new__`, so
``safe_load`` is not a style preference here, it is the security boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from cvassure.core.errors import ConfigError
from cvassure.core.hashing import canonical_sha256

MAX_CONFIG_BYTES = 512 * 1024
# ponytail: a fixed ceiling, not a quota system. Raise it only if a real config
# needs it; a 512 KB YAML file with a billion detectors is an attack, not a use case.
UNKNOWN_TOP_LEVEL = "unknown top-level key"


@dataclass(frozen=True)
class LinkConfig:
    tau_link: float = 0.5
    identity_weight: float = 0.5
    overlap_weight: float = 0.2
    pattern_weight: float = 0.3
    calibration: str = "UNCALIBRATED"


@dataclass(frozen=True)
class RunConfig:
    seed: int = 42
    policy_path: Path = Path("policies/default.yaml")
    detector_modules: tuple[str, ...] = ()
    detector_order: tuple[str, ...] = ()
    timeouts: dict[str, float] = field(default_factory=dict)
    adapters: dict[str, str] = field(default_factory=dict)
    link: LinkConfig = field(default_factory=LinkConfig)
    access: str = "white-box"
    raw: dict[str, Any] = field(default_factory=dict)
    config_hash: str = ""
    source: Path | None = None


def load_yaml(path: Path) -> Any:
    """`safe_load` and a size ceiling. Raises ConfigError, never returns junk."""
    if not path.is_file():
        raise ConfigError(f"no such file: {path}")
    size = path.stat().st_size
    if size > MAX_CONFIG_BYTES:
        raise ConfigError(f"{path} is {size} bytes, over the {MAX_CONFIG_BYTES} byte limit")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        # Includes the !!python/object case: safe_load refuses to construct it.
        raise ConfigError(f"{path} is not safe-loadable YAML: {exc}") from exc


def _require(doc: dict[str, Any], key: str, kind: type, default: Any) -> Any:
    if key not in doc:
        return default
    value = doc[key]
    if not isinstance(value, kind):
        raise ConfigError(f"{key!r} must be {kind.__name__}, got {type(value).__name__}")
    return value


def load_config(path: Path | None) -> RunConfig:
    """Load and validate a run config. Missing file = defaults, which is legal."""
    if path is None:
        cfg = RunConfig()
        return RunConfig(**{**cfg.__dict__, "config_hash": canonical_sha256({})})
    doc = load_yaml(path)
    if doc is None:
        doc = {}
    if not isinstance(doc, dict):
        raise ConfigError(f"{path} must contain a mapping at the top level")

    known = {
        "seed",
        "policy",
        "detectors",
        "timeouts",
        "adapters",
        "link",
        "access",
        "version",
        "name",
    }
    unknown = sorted(set(doc) - known)
    if unknown:
        raise ConfigError(f"{path}: {UNKNOWN_TOP_LEVEL}: {', '.join(unknown)}")

    seed = _require(doc, "seed", int, 42)
    access = _require(doc, "access", str, "white-box")
    if access not in ("white-box", "gray-box", "black-box", "not-applicable"):
        raise ConfigError(f"access must be a tier name, got {access!r}")

    link_doc = _require(doc, "link", dict, {})
    link = LinkConfig(
        tau_link=float(_require(link_doc, "tau_link", (int, float), 0.5)),
        identity_weight=float(_require(link_doc, "identity", (int, float), 0.5)),
        overlap_weight=float(_require(link_doc, "overlap", (int, float), 0.2)),
        pattern_weight=float(_require(link_doc, "pattern", (int, float), 0.3)),
        calibration=str(_require(link_doc, "calibration", str, "UNCALIBRATED")),
    )
    if not 0.0 <= link.tau_link <= 1.0:
        raise ConfigError(f"link.tau_link must be in [0, 1], got {link.tau_link}")
    for name, w in (
        ("identity", link.identity_weight),
        ("overlap", link.overlap_weight),
        ("pattern", link.pattern_weight),
    ):
        if w < 0:
            raise ConfigError(f"link.{name} weight must be >= 0, got {w}")

    detectors = _require(doc, "detectors", dict, {})
    modules = tuple(_require(detectors, "modules", list, []))
    order = tuple(_require(detectors, "order", list, []))

    return RunConfig(
        seed=seed,
        policy_path=Path(_require(doc, "policy", str, "policies/default.yaml")),
        detector_modules=modules,
        detector_order=order,
        timeouts={str(k): float(v) for k, v in _require(doc, "timeouts", dict, {}).items()},
        adapters={str(k): str(v) for k, v in _require(doc, "adapters", dict, {}).items()},
        link=link,
        access=access,
        raw=doc,
        config_hash=canonical_sha256(doc),
        source=path,
    )
