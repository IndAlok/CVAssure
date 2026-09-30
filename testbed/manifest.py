"""Data contracts, manifest schema, validation, digest, and save/load functions for scenarios and timelines."""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any
import numpy as np


@dataclass
class Scenario:
    """Represents an attack scenario containing images, labels, and ground truth metadata."""

    name: str
    seed: int
    dataset: str
    X: np.ndarray
    y_given: np.ndarray
    y_true: np.ndarray
    sample_id: np.ndarray
    contributor: np.ndarray
    batch: np.ndarray
    attack_bits: np.ndarray
    dup_of: np.ndarray
    attack_names: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)

    def is_attacked(self, name: str | None = None) -> np.ndarray:
        """Return boolean mask (N,) indicating attacked samples.

        If name is None, returns True for any attacked sample.
        If name is provided, returns True for samples hit by that specific attack.
        """
        if name is None:
            return self.attack_bits != 0

        if name not in self.attack_names:
            return np.zeros(len(self.X), dtype=bool)

        bit_idx = self.attack_names.index(name)
        return (self.attack_bits & (1 << bit_idx)) != 0

    def ids(self, name: str) -> list[int]:
        """Return list of sample_id integers hit by the specified attack."""
        mask = self.is_attacked(name)
        return [int(sid) for sid in self.sample_id[mask]]


@dataclass
class Batch:
    """Represents a time-ordered batch of samples in a timeline."""

    t: int
    X: np.ndarray
    y_given: np.ndarray
    contributor: np.ndarray
    is_attacked: np.ndarray
    shift_strength: float


@dataclass
class Timeline:
    """Represents a time-series of batches for shift testing."""

    name: str
    seed: int
    kind: str  # "drift" | "manipulation" | "none" | "ambiguous"
    batches: list[Batch] = field(default_factory=list)


@dataclass
class DetectorOutput:
    """Standardized output schema for attack and shift detectors."""

    scores: np.ndarray | None  # per-sample anomaly/suspicion scores
    findings: list[dict[str, Any]]
    meta: dict[str, Any]


def validate_scenario(sc: Scenario) -> None:
    """Validate scenario fields and raise ValueError on any structural inconsistency."""
    n = len(sc.X)

    # 1. Array length checks
    array_fields = {
        "y_given": sc.y_given,
        "y_true": sc.y_true,
        "sample_id": sc.sample_id,
        "contributor": sc.contributor,
        "batch": sc.batch,
        "attack_bits": sc.attack_bits,
        "dup_of": sc.dup_of,
    }
    for field_name, arr in array_fields.items():
        if len(arr) != n:
            raise ValueError(
                f"Array length mismatch for '{field_name}': expected {n}, got {len(arr)}"
            )

    # 2. Image dtype & shape
    if sc.X.dtype != np.uint8:
        raise ValueError(f"Image array X must be uint8, got {sc.X.dtype}")
    if sc.X.ndim != 4 or sc.X.shape[3] != 3:
        raise ValueError(f"Image array X must have shape (N, H, W, 3), got {sc.X.shape}")

    # 3. Unique sample_id
    if len(np.unique(sc.sample_id)) != n:
        raise ValueError("sample_id contains non-unique values")

    # 4. attack_bits range
    max_bit = len(sc.attack_names)
    max_val = (1 << max_bit) - 1
    if np.any(sc.attack_bits < 0) or np.any(sc.attack_bits > max_val):
        raise ValueError(f"attack_bits contain values out of valid range [0, {max_val}]")

    # 5. dup_of valid reference
    valid_ids = set(sc.sample_id)
    valid_ids.add(-1)
    for dup in sc.dup_of:
        if int(dup) not in valid_ids:
            raise ValueError(f"dup_of references unknown sample_id: {dup}")

    # 6. y_given and y_true valid non-negative labels
    if np.any(sc.y_given < 0) or np.any(sc.y_true < 0):
        raise ValueError("Labels in y_given or y_true contain negative values")


def scenario_digest(sc: Scenario) -> str:
    """Compute sha256 hex digest over scenario arrays and metadata with fixed key ordering."""
    hasher = hashlib.sha256()

    # Meta header
    header = f"{sc.name}:{sc.seed}:{sc.dataset}:{sc.attack_names}".encode("utf-8")
    hasher.update(header)

    # Array content in strict order
    ordered_keys = [
        ("X", sc.X),
        ("y_given", sc.y_given),
        ("y_true", sc.y_true),
        ("sample_id", sc.sample_id),
        ("contributor", sc.contributor),
        ("batch", sc.batch),
        ("attack_bits", sc.attack_bits),
        ("dup_of", sc.dup_of),
    ]

    for name, arr in ordered_keys:
        hasher.update(name.encode("utf-8"))
        hasher.update(str(arr.shape).encode("utf-8"))
        hasher.update(str(arr.dtype).encode("utf-8"))
        hasher.update(np.ascontiguousarray(arr).tobytes())

    params_str = json.dumps(sc.params, sort_keys=True)
    hasher.update(params_str.encode("utf-8"))

    return f"sha256:{hasher.hexdigest()}"


def ground_truth_ids(sc: Scenario) -> dict[str, list[int]]:
    """Return dictionary mapping attack names to list of affected sample_ids."""
    return {name: sc.ids(name) for name in sc.attack_names}


def save_scenario(sc: Scenario, out_dir: str | Path) -> Path:
    """Validate scenario and write data.npz and manifest.json to out_dir."""
    validate_scenario(sc)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    digest = scenario_digest(sc)

    # Save data.npz
    np.savez_compressed(
        out_path / "data.npz",
        X=sc.X,
        y_given=sc.y_given,
        y_true=sc.y_true,
        sample_id=sc.sample_id,
        contributor=sc.contributor,
        batch=sc.batch,
        attack_bits=sc.attack_bits,
        dup_of=sc.dup_of,
    )

    # Save manifest.json
    contributors = sorted(list(set(str(c) for c in sc.contributor)))
    n_batches = int(len(set(sc.batch.tolist())))

    manifest_data = {
        "scenario": sc.name,
        "seed": sc.seed,
        "dataset": sc.dataset,
        "n_samples": len(sc.X),
        "attack_names": sc.attack_names,
        "contributors": contributors,
        "n_batches": n_batches,
        "attack_params": sc.params,
        "ground_truth": ground_truth_ids(sc),
        "digest": digest,
        "tool": "cvassure-testbed 0.1",
    }

    with open(out_path / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return out_path


def load_scenario(path: str | Path) -> Scenario:
    """Load scenario from directory containing manifest.json and data.npz, verifying digest and integrity."""
    target_path = Path(path)
    if target_path.is_file():
        out_dir = target_path.parent
    else:
        out_dir = target_path

    manifest_file = out_dir / "manifest.json"
    data_file = out_dir / "data.npz"

    if not manifest_file.exists() or not data_file.exists():
        raise FileNotFoundError(f"Missing manifest.json or data.npz in {out_dir}")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with np.load(data_file, allow_pickle=True) as data:
        sc = Scenario(
            name=manifest["scenario"],
            seed=manifest["seed"],
            dataset=manifest["dataset"],
            X=data["X"],
            y_given=data["y_given"],
            y_true=data["y_true"],
            sample_id=data["sample_id"],
            contributor=data["contributor"],
            batch=data["batch"],
            attack_bits=data["attack_bits"],
            dup_of=data["dup_of"],
            attack_names=manifest.get("attack_names", []),
            params=manifest.get("attack_params", {}),
        )

    computed_digest = scenario_digest(sc)
    if computed_digest != manifest.get("digest"):
        raise ValueError(
            f"Scenario digest mismatch! Stored: {manifest.get('digest')}, Computed: {computed_digest}"
        )

    validate_scenario(sc)
    return sc
