"""Thin COCO / YOLO readers. Enough for the day-2 pipeline, nothing more.

Person 2 owns the full adapters and may replace this file wholesale. This exists
so stage 1 does something real on day 2 while P2 is still writing the proper one.

The internal sample table is the contract: `sample_id`, `path`, `class_id`,
`source_id`, `batch_id`. Contributor and batch come from extra annotation fields
or a sidecar JSON, **never** from the ground-truth attack manifest.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cvassure.core.detector import Dataset, Sample

#: Annotation keys checked, in order, for a contributor id. First hit wins.
SOURCE_KEYS = ("contributor_id", "source_id", "contributor", "source")
#: ...and for a batch id.
BATCH_KEYS = ("batch_id", "batch", "collection_id")

MAX_SAMPLES = 200_000


class AdapterError(ValueError):
    """The dataset could not be read. Exit 2: a usage or input error."""


def _first(d: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for k in keys:
        v = d.get(k)
        if isinstance(v, (str, int)) and str(v):
            return str(v)
    return None


def read_coco(root: Path, sidecar: dict[str, Any] | None = None) -> Dataset:
    """COCO detection JSON. `root` is the directory holding the json and images."""
    sidecar = sidecar or {}
    candidates = sorted(p for p in root.glob("*.json") if p.name not in ("sidecar.json",))
    if not candidates:
        raise AdapterError(f"no COCO json found in {root}")
    path = next((p for p in candidates if "instances" in p.name or "coco" in p.name), candidates[0])
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError(f"{path} is not readable COCO json: {exc}") from exc

    images = {str(i["id"]): i.get("file_name", f"{i['id']}.jpg") for i in doc.get("images", [])}
    if not images:
        raise AdapterError(f"{path} has no images[]")

    ann_by_image: dict[str, dict[str, Any]] = {}
    for ann in doc.get("annotations", []):
        img = str(ann.get("image_id"))
        if img not in ann_by_image:
            ann_by_image[img] = ann

    samples: list[Sample] = []
    for img_id, file_name in images.items():
        ann = ann_by_image.get(img_id, {})
        source = _first(ann, SOURCE_KEYS) or _first(images_meta(doc, img_id), SOURCE_KEYS)
        batch = _first(ann, BATCH_KEYS) or _first(images_meta(doc, img_id), BATCH_KEYS)
        if source is None:
            source = sidecar.get("source_by_image", {}).get(img_id)
        if batch is None:
            batch = sidecar.get("batch_by_image", {}).get(img_id)
        samples.append(
            Sample(
                sample_id=img_id,
                path=root / file_name,
                class_id=ann.get("category_id"),
                source_id=source,
                batch_id=batch,
            )
        )
        if len(samples) >= MAX_SAMPLES:
            break
    return Dataset(root=root, format="coco", samples=tuple(samples), sidecar=sidecar)


def images_meta(doc: dict[str, Any], image_id: str) -> dict[str, Any]:
    for i in doc.get("images", []):
        if str(i.get("id")) == image_id:
            return i
    return {}


def read_yolo(root: Path, sidecar: dict[str, Any] | None = None) -> Dataset:
    """YOLO `labels/*.txt`, one row per class per object, plus an images list.

    YOLO has no metadata slot, so `source_id` and `batch_id` must come from the
    sidecar. That is the honest answer, not a guess: if the sidecar is missing
    they stay `None` and source-level aggregation is not possible for this
    dataset. Coverage says so rather than inventing a contributor.
    """
    sidecar = sidecar or {}
    labels = root / "labels"
    if not labels.is_dir():
        raise AdapterError(f"no YOLO labels/ directory in {root}")
    source_by_sample = sidecar.get("source_by_sample", {})
    batch_by_sample = sidecar.get("batch_by_sample", {})

    samples: list[Sample] = []
    for label in sorted(labels.glob("*.txt")):
        sample_id = label.stem
        classes: list[int] = []
        for line in label.read_text(encoding="utf-8").splitlines():
            head = line.split()
            if head and head[0].lstrip("-").isdigit():
                classes.append(int(head[0]))
        samples.append(
            Sample(
                sample_id=sample_id,
                path=(root / "images" / f"{sample_id}.jpg"),
                class_id=classes[0] if classes else None,
                source_id=source_by_sample.get(sample_id),
                batch_id=batch_by_sample.get(sample_id),
            )
        )
        if len(samples) >= MAX_SAMPLES:
            break
    if not samples:
        raise AdapterError(f"no label files in {labels}")
    return Dataset(root=root, format="yolo", samples=tuple(samples), sidecar=sidecar)


def load_sidecar(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError(f"sidecar {path} is not readable json: {exc}") from exc
    return doc if isinstance(doc, dict) else {}


ADAPTERS = {"coco": read_coco, "yolo": read_yolo}


def load_dataset(path: Path, sidecar: dict[str, Any] | None = None) -> Dataset:
    """Pick an adapter by content, not by file extension.

    A directory with `labels/` is YOLO; a directory with a COCO json is COCO.
    The plan requires ingesting both without a format flag.
    """
    if not path.is_dir():
        raise AdapterError(f"no such data directory: {path}")
    sidecar = sidecar or {}
    if (path / "labels").is_dir():
        return read_yolo(path, sidecar)
    for name in ADAPTERS:
        for candidate in sorted(path.glob("*.json")):
            if name == "coco" and "instances" in candidate.name:
                return read_coco(path, sidecar)
    # Fall back to any json that parses as COCO.
    return read_coco(path, sidecar)
