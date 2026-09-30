"""SYNTHETIC test data. Generated, not stored. No real images, no real datasets.

Person 5 owns `build_demo_scenario(seed=42)` (`contracts/MANIFEST.md`). Until it
lands, this stands in so the day-2 pipeline is never the thing that is late.

The contributor ids here (`C-01`, `C-07`) are FIXTURE VALUES in the demo story.
They live here and in test assertions, never in policy, linker, or core logic.
The linker and the CLI read them from the data, which is the whole point of the
scenario-agnostic rule.

Contents: a small COCO dataset with contributor and batch metadata split into a
clean contributor and a poisoned one, a JSON Lines record file, and a real
minimal ONNX graph.

The ONNX file is a genuine single-node ONNX model, not a placeholder. It exists
so day-2 work is not blocked by Person 3: the pipeline's model stage must run and
the cross-asset link must fire before P3's wrapper lands. It is **not** a trained
classifier and carries **no** backdoor. Every detector that reads it is therefore
labelled a stub, and a real detector must not draw conclusions from it. Person 3
and Person 5 replace it with a real backdoored model.
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
#: this; a real detector measures it.
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
                    # where the day-2 reader looks first.
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
    """JSON Lines inference records. Unsigned: P4's chain is not in yet.

    The file is well-formed so the record stage has something real to count. It
    is NOT a valid P4 chain, and the stub says so in its `limitations`.
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
    """A real, tiny, valid ONNX graph. Not a placeholder, not a real classifier.

    Why a genuine ONNX file: the model stage, the cross-asset link and the report
    all need a model to exist, and blocking day-2 work on Person 3's wrapper would
    make the whole spine untestable. A real ONNX file lets a loader open something
    real, which is what makes the day-2 run honest instead of theatrical.

    What it is **not**: a trained classifier, a backdoored model, or evidence of
    anything. It is `Identity` over a 1x3x32x32 input, so it loads, runs, and
    produces nothing interesting. It carries no trigger, and every finding a
    detector draws from it is stamped `stub: true` for exactly this reason.

    Person 3 supplies the wrapper, Person 5 supplies the backdoored demo model,
    and both replace this.

    Also writes `model.onnx.digest.txt` with the sha256, so a test can prove the
    digest the pipeline recorded is the digest of the bytes on disk.
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
