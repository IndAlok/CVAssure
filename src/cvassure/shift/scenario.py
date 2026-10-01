import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def generate_seeded_attacks(base_dir: Path, out_dir: Path, seed: int = 42) -> dict[str, Any]:
    """Generates datasets with seeded attacks for the testbed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    _rng = np.random.default_rng(seed)

    # 1. Label Flips
    # (Just logical flips in sidecar or metadata)

    # 2. Patch Trigger
    def add_patch(img_path: Path, patch_size: int = 8) -> None:
        with Image.open(img_path) as img:
            arr = np.array(img.convert("RGB"))
            # Add blue patch top-left
            arr[:patch_size, :patch_size] = [0, 0, 255]
            Image.fromarray(arr).save(img_path)

    # In a real implementation we would copy base_dir to out_dir,
    # then iterate and apply these functions to subsets of data.
    # For this structure, we return a mock manifest.

    manifest = {
        "label_flips": {"rate": 0.15, "affected_samples": []},
        "patch_trigger": {"patch_size": 8, "affected_samples": []},
        "ood_insertion": {"count": 50},
    }

    manifest_path = out_dir / "attack_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return manifest


def build_demo_scenario(seed: int = 42) -> dict[str, Path]:
    """Build the demonstration scenario for evaluation."""
    # Dummy paths for the sake of architecture completion
    # Real testbed uses the generated paths
    return {
        "data": Path("data/demo"),
        "model": Path("model/demo.onnx"),
        "records": Path("records/demo.jsonl"),
    }
