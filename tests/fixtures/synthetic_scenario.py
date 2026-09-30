"""Synthetic test data. Generated, not stored. No real images, no real datasets.

The contributor ids here, `C-01` and `C-07`, are fixture values. They live here
and in test assertions. Policy, the linker, and core logic do not hard-code them.

Contents: a small COCO dataset with contributor and batch metadata, a JSON Lines
record file, and a minimal ONNX graph.

The ONNX file is a real single-node graph. It is not a trained classifier and it
has no backdoor. Detectors that treat it as a result must mark themselves as stubs.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from cvassure.core.imaging import solid

#: Two contributors. `C-01` is clean, `C-07` carries the fixture patch. The split
#: matters: the linker and the demo story are only meaningful if the data finding
#: and the clean samples come from *different* sources.
CLEAN_CONTRIBUTOR = "C-01"
POISONED_CONTRIBUTOR = "C-07"
CONTRIBUTORS = (CLEAN_CONTRIBUTOR, POISONED_CONTRIBUTOR)
BATCHES = ("B-1", "B-2", "B-3")
N_PER_CONTRIBUTOR = 4
RECORD_COUNT = 12
#: Which contributor's samples carry the frozen patch. `PatchTriggerStub` reads
#: this. A real detector measures it.
PATCHED_CONTRIBUTOR = POISONED_CONTRIBUTOR


def build_dataset(root: Path) -> Path:
    """A COCO-style detection json plus placeholder image files."""
    root.mkdir(parents=True, exist_ok=True)
    images, annotations = [], []
    ann_id = 1
    for ci, source in enumerate(CONTRIBUTORS):
        for i in range(N_PER_CONTRIBUTOR):
            img_id = f"{ci * N_PER_CONTRIBUTOR + i + 1}"
            batch = BATCHES[ci % len(BATCHES)]
            name = f"img_{img_id}.png"
            images.append(
                {
                    "id": img_id,
                    "file_name": name,
                    # Contributor metadata as extra annotation fields, which is
                    # Annotation file the COCO reader opens first.
                    "contributor_id": source,
                    "batch_id": batch,
                }
            )
            annotations.append(
                {
                    "id": str(ann_id),
                    "image_id": img_id,
                    "category_id": 0,
                    "bbox": [10, 10, 20, 20],
                    "area": 400,
                    "iscrowd": 0,
                    "contributor_id": source,
                    "batch_id": batch,
                }
            )
            ann_id += 1
            solid(root / name, 32, 32, (40 * ci % 256, 90, 150))

    (root / "instances_synthetic.json").write_text(
        json.dumps(
            {
                "info": {
                    "description": "SYNTHETIC fixture. No real images, no real dataset.",
                    "version": "0.1.0",
                },
                "licenses": [{"name": "synthetic", "url": ""}],
                "images": images,
                "annotations": annotations,
                "categories": [{"id": 0, "name": "class0"}, {"id": 1, "name": "class1"}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return root


def build_records(path: Path, count: int = RECORD_COUNT) -> Path:
    """JSON Lines inference records. Unsigned.

    The file is well-formed so the record stage has something to count. It is not
    a signed chain, and the stub says so in `limitations`.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(count):
        lines.append(
            json.dumps(
                {
                    "record_id": f"rec-{i:04d}",
                    "input_hash": f"sha256:{(i * 2654435761) % (1 << 64):016x}",
                    "model_digest": "sha256:model-fixture",
                    "config_hash": "sha256:config-fixture",
                    "output": {"label": i % 2, "score": round(0.5 + (i % 5) / 20, 3)},
                    "nonce": f"{i:08x}",
                    "sequence": i,
                    "timestamp": "2026-09-30T09:00:00Z",
                    "prev_hash": "sha256:genesis",
                    "signature": None,
                    "synthetic": True,
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _onnx_fixture_bytes() -> bytes:
    """A minimal valid ONNX ModelProto: Identity over 1x3x32x32 float."""
    shape = [1, 3, 32, 32]
    n = 1
    for d in shape:
        n *= d
    weights = struct.pack(f"<{n}f", *([0.0] * n))

    # TensorProto: dims, data_type=1 (FLOAT), name, raw_data
    tensor = (
        _pb(1, _pack_varints(shape))
        + _pb(2, _pack_varints([1]))
        + _pb(8, b"identity")
        + _pb(9, weights)
    )
    # NodeProto: input x, output y, op_type Identity, name
    node = _pb(1, b"x") + _pb(2, b"y") + _pb(3, b"Identity") + _pb(4, b"identity")
    # ValueInfoProto: name, type.tensor_type{elem_type, shape}
    dims = b"".join(_pb(1, _pb(1, _pack_varints([d]))) for d in shape)
    vtype = _pb(1, _pack_varints([1])) + _pb(2, _pb(1, dims))

    def value(name: bytes) -> bytes:
        return _pb(1, name) + _pb(2, _pb(1, vtype))

    graph = (
        _pb(1, node)
        + _pb(2, b"cvassure_fixture_graph")
        + _pb(5, tensor)
        + _pb(11, value(b"x"))
        + _pb(12, value(b"y"))
    )
    opset = _pb(1, b"") + _pb(2, _pack_varints([13]))
    return _pb(1, _pack_varints([7])) + _pb(2, b"cvassure") + _pb(7, graph) + _pb(8, opset)


def build_model_fixture(path: Path) -> Path:
    """A real, tiny ONNX graph. Identity over a 1x3x32x32 input.

    It is not a trained classifier and it has no trigger. A finding drawn from
    it is a stub. Also writes `model.onnx.digest.txt` with the SHA-256.
    """
    import hashlib

    payload = _onnx_fixture_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    path.with_suffix(path.suffix + ".digest.txt").write_text(
        hashlib.sha256(payload).hexdigest() + "\n", encoding="utf-8"
    )
    return path


def _pack_varints(values: list[int]) -> bytes:
    """protobuf variable-length integers, little-endian base-128, 7 bits per byte."""
    out = bytearray()
    for v in values:
        while True:
            byte = v & 0x7F
            v >>= 7
            out.append(byte | (0x80 if v else 0))
            if not v:
                break
    return bytes(out)


def _pb(field: int, payload: bytes) -> bytes:
    """One protobuf field: tag then length-delimited payload."""
    return _pack_varints([(field << 3) | 2]) + _pack_varints([len(payload)]) + payload


def build_all(root: Path) -> dict[str, Path]:
    """Everything the audit command needs, in one call."""
    return {
        "data": build_dataset(root / "data"),
        "model": build_model_fixture(root / "model.onnx"),
        "records": build_records(root / "records.jsonl"),
    }
