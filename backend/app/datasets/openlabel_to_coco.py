"""OpenLABEL -> COCO, so doc 31's importer can read a rail dataset unchanged.

Separate from `openlabel.py` for the 300-line rule, and the seam is honest: that module
*reads* OpenLABEL and knows nothing about COCO, this one *writes* COCO and knows nothing
about how the shapes were parsed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.datasets.coco_import import COCO_FILENAME
from app.datasets.openlabel import (
    MIN_BOX_PIXELS,
    ConversionSummary,
    box_from_bbox,
    box_from_poly2d,
    frame_image,
)

logger = logging.getLogger(__name__)

Box = tuple[float, float, float, float]


def convert(
    root: dict[str, Any],
    camera: str,
    *,
    exclude: frozenset[str] = frozenset(),
    min_pixels: float = MIN_BOX_PIXELS,
) -> tuple[dict[str, Any], ConversionSummary]:
    """One camera's boxes as a COCO document, plus what was dropped getting there.

    `exclude` names object types to leave out entirely. OSDaR23 needs it for `track`: an
    open polyline to the horizon has no useful bounding box, and its extent would teach a
    detector that the class means "most of the image".
    """
    objects = root["objects"]
    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    categories: dict[str, int] = {}
    summary = _Counters()

    for frame_id in sorted(root["frames"], key=_as_int):
        frame = root["frames"][frame_id]
        file_name = frame_image(frame, camera)
        if file_name is None:
            # This frame has no image for this camera. Legitimate — sensors are not all
            # sampled at the same rate — and not an error.
            continue

        image_id = len(images) + 1
        images.append({"id": image_id, "file_name": file_name})

        for object_id, entry in frame.get("objects", {}).items():
            type_name = objects.get(object_id, {}).get("type")
            if not isinstance(type_name, str) or type_name in exclude:
                if isinstance(type_name, str):
                    summary.excluded.add(type_name)
                continue
            for box in _boxes_for(entry, camera, summary):
                if box[2] < min_pixels or box[3] < min_pixels:
                    summary.tiny += 1
                    continue
                category_id = categories.setdefault(type_name, len(categories) + 1)
                annotations.append(
                    {
                        "id": len(annotations) + 1,
                        "image_id": image_id,
                        "category_id": category_id,
                        "bbox": [round(v, 2) for v in box],
                        "area": round(box[2] * box[3], 2),
                        "iscrowd": 0,
                    }
                )

    document = {
        "info": {"description": f"Converted from ASAM OpenLABEL, camera {camera}"},
        "images": images,
        "annotations": annotations,
        "categories": [
            {"id": index, "name": name, "supercategory": "none"}
            for name, index in sorted(categories.items(), key=lambda item: item[1])
        ],
    }
    return document, summary.finish(len(images), len(annotations), tuple(categories))


class _Counters:
    """Mutable while converting; frozen into a `ConversionSummary` at the end."""

    def __init__(self) -> None:
        self.open_polylines = 0
        self.tiny = 0
        self.other_sensors = 0
        self.excluded: set[str] = set()

    def finish(self, images: int, boxes: int, names: tuple[str, ...]) -> ConversionSummary:
        return ConversionSummary(
            images=images,
            boxes=boxes,
            class_names=names,
            skipped_open_polylines=self.open_polylines,
            skipped_tiny=self.tiny,
            skipped_other_sensors=self.other_sensors,
            excluded_classes=tuple(sorted(self.excluded)),
        )


def _boxes_for(entry: dict[str, Any], camera: str, counters: _Counters) -> list[Box]:
    """Every box this object contributes to this camera's frame.

    Both shapes are read because OSDaR23 uses both for things that *are* boxes: `person`
    and `signal_pole` are annotated as `bbox`, `signal` as a closed four-point quad.
    """
    data = entry.get("object_data", {})
    found: list[Box] = []

    for shape in data.get("bbox", []):
        if not _is_camera(shape, camera, counters):
            continue
        box = box_from_bbox(shape)
        if box is not None:
            found.append(box)

    for shape in data.get("poly2d", []):
        if not _is_camera(shape, camera, counters):
            continue
        box = box_from_poly2d(shape)
        if box is None:
            counters.open_polylines += 1
            continue
        found.append(box)

    return found


def _is_camera(shape: dict[str, Any], camera: str, counters: _Counters) -> bool:
    """The single most important check in this module — see `openlabel.py`'s docstring."""
    if shape.get("coordinate_system") == camera:
        return True
    counters.other_sensors += 1
    return False


def _as_int(key: str) -> int:
    try:
        return int(key)
    except ValueError:  # pragma: no cover - OSDaR23 numbers its frames
        return 0


def write_coco(document: dict[str, Any], directory: Path) -> Path:
    """Write the document where `find_coco_files` will find it."""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / COCO_FILENAME
    target.write_text(json.dumps(document), encoding="utf-8")
    logger.info(
        "Wrote %d image(s) and %d box(es) to %s",
        len(document["images"]),
        len(document["annotations"]),
        target,
    )
    return target


__all__ = ["convert", "write_coco"]
