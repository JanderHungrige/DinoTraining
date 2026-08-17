"""COCO export.

Positive boxes only. COCO annotations assert "an object is here"; a negative or an
unclear box asserts the opposite or nothing, and writing them as annotations would
teach any downstream consumer exactly the wrong thing. They stay in the native
manifest, where Wave 2's trainer can use them as hard negatives.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.datasets.models import Box

COCO_FILENAME = "annotations.coco.json"

# One category for Wave 1: the annotation loop is "is this the thing you prompted
# for, yes/no". Multi-class arrives with the Wave 2 head types.
DEFAULT_CATEGORY = {"id": 1, "name": "object", "supercategory": "none"}


def build_coco(
    dataset_name: str,
    images: list[tuple[int, str, int, int, list[Box]]],
    prompt: str | None = None,
) -> dict[str, Any]:
    """Build a COCO-shaped dict from stored annotations."""
    coco_images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    annotation_id = 1

    for image_id, path, width, height, boxes in images:
        coco_images.append(
            {
                "id": image_id,
                "file_name": Path(path).name,
                "path": path,
                "width": width,
                "height": height,
            }
        )
        for box in boxes:
            if box.label != "positive":
                continue
            annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": DEFAULT_CATEGORY["id"],
                    # COCO bbox is [x, y, width, height] top-left origin — the same
                    # convention the store uses, so this is a copy, not a conversion.
                    "bbox": [box.x, box.y, box.w, box.h],
                    "area": box.w * box.h,
                    "iscrowd": 0,
                    **({"score": box.score} if box.score is not None else {}),
                }
            )
            annotation_id += 1

    return {
        "info": {
            "description": dataset_name,
            "version": "1.0",
            "date_created": datetime.now(UTC).isoformat(timespec="seconds"),
            "generator": "DinoTraining",
            **({"prompt": prompt} if prompt else {}),
        },
        "licenses": [],
        "images": coco_images,
        "annotations": annotations,
        "categories": [DEFAULT_CATEGORY],
    }


def write_coco(directory: Path, coco: dict[str, Any]) -> Path:
    """Write the export next to the native manifest."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / COCO_FILENAME
    path.write_text(json.dumps(coco, indent=2), encoding="utf-8")
    return path
