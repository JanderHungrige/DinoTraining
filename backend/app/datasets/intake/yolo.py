"""YOLO (Ultralytics, Roboflow "YOLOv5/v8" exports) as COCO documents (doc 136).

Layout: pictures in an `images` folder, one `.txt` per picture in the matching `labels`
folder (`images/train/x.jpg` ↔ `labels/train/x.txt`, or `train/images` ↔ `train/labels`).
A line is `class cx cy w h`, normalised to the picture; a longer line is a polygon
`class x1 y1 x2 y2 …`. Class names come from `data.yaml` (`names`) or `classes.txt`.

A picture without a label file has no objects: that is YOLO's meaning, so it is imported
as annotated and empty (a background picture), as doc 31 keeps them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.cloud.pictures import picture_exists, picture_size
from app.datasets.coco_import import split_of
from app.datasets.intake.documents import Document
from app.datasets.intake.walk import Listing


def is_yolo(listing: Listing) -> bool:
    return any(_labels_dir(path) is not None for path in listing.txt_files)


def _labels_dir(path: Path) -> Path | None:
    """The `labels` folder this label file sits under, if any."""
    for parent in path.parents:
        if parent.name == "labels":
            return parent
    return None


def class_names(listing: Listing) -> list[str]:
    for path in listing.yaml_files:
        names = _names_from_yaml(path.read_text(encoding="utf-8", errors="ignore"))
        if names:
            return names
    for path in listing.txt_files:
        if path.name in {"classes.txt", "obj.names"}:
            return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    return []


def _names_from_yaml(text: str) -> list[str]:
    """`names: [a, b]`, a block list, or `0: a` lines; no YAML library needed."""
    inline = re.search(r"^names\s*:\s*\[(.*?)\]", text, re.MULTILINE | re.DOTALL)
    if inline:
        return [n.strip().strip("'\"") for n in inline.group(1).split(",") if n.strip()]
    block = re.search(r"^names\s*:\s*\n((?:[ \t]+.*\n?)+)", text, re.MULTILINE)
    if not block:
        return []
    names: list[str] = []
    for line in block.group(1).splitlines():
        item = re.match(r"\s*(?:-\s*|\d+\s*:\s*)(.+)", line)
        if item:
            names.append(item.group(1).strip().strip("'\""))
    return names


def _picture_for(label: Path, labels_dir: Path) -> Path | None:
    images_dir = labels_dir.with_name("images")
    stem = images_dir / label.relative_to(labels_dir).with_suffix("")
    for suffix in (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"):
        for candidate in (stem.with_suffix(suffix), stem.with_suffix(suffix.upper())):
            if picture_exists(candidate):  # a bucket's picture is listed, not local
                return candidate
    return None


def yolo_documents(listing: Listing) -> list[Document]:
    names = class_names(listing)
    by_split: dict[str | None, dict[str, Any]] = {}
    labelled: set[Path] = set()
    for label in listing.txt_files:
        labels_dir = _labels_dir(label)
        picture = _picture_for(label, labels_dir) if labels_dir else None
        if picture is None:
            continue
        labelled.add(picture)
        _add(by_split, listing.root, picture, label, names)
    # Pictures in an `images` folder without a label file: YOLO's background pictures.
    for picture in listing.pictures:
        if picture not in labelled and "images" in picture.relative_to(listing.root).parts:
            _add(by_split, listing.root, picture, None, names)
    return [
        Document(doc, listing.root, listing.root / "labels", split)
        for split, doc in by_split.items()
    ]


def _add(
    by_split: dict[str | None, dict[str, Any]],
    root: Path,
    picture: Path,
    label: Path | None,
    names: list[str],
) -> None:
    relative = picture.relative_to(root)
    split = next((split_of(part) for part in relative.parts if split_of(part)), None)
    doc = by_split.setdefault(split, {"images": [], "annotations": [], "categories": []})
    try:
        width, height = picture_size(picture)  # a bucket's: from its header (doc 148)
    except OSError:
        return
    image_id = len(doc["images"]) + 1
    doc["images"].append(
        {"id": image_id, "file_name": str(relative), "width": width, "height": height}
    )
    if label is None:
        return
    for line in label.read_text(encoding="utf-8", errors="ignore").splitlines():
        values = line.split()
        if len(values) < 5:
            continue
        category = _category(doc, names, int(float(values[0])))
        numbers = [float(v) for v in values[1:]]
        doc["annotations"].append(
            _annotation(len(doc["annotations"]) + 1, image_id, category, numbers, width, height)
        )


def _category(doc: dict[str, Any], names: list[str], index: int) -> int:
    name = names[index] if 0 <= index < len(names) else f"class_{index}"
    for category in doc["categories"]:
        if category["name"] == name:
            return int(category["id"])
    doc["categories"].append({"id": len(doc["categories"]) + 1, "name": name})
    return len(doc["categories"])


def _annotation(
    annotation_id: int, image_id: int, category: int, numbers: list[float], width: int, height: int
) -> dict[str, Any]:
    if len(numbers) == 4:
        cx, cy, w, h = numbers
        bbox = [(cx - w / 2) * width, (cy - h / 2) * height, w * width, h * height]
        return {"id": annotation_id, "image_id": image_id, "category_id": category, "bbox": bbox}
    xs = [x * width for x in numbers[0::2]]
    ys = [y * height for y in numbers[1::2]]
    polygon = [coordinate for pair in zip(xs, ys, strict=False) for coordinate in pair]
    bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
    return {
        "id": annotation_id,
        "image_id": image_id,
        "category_id": category,
        "bbox": bbox,
        "segmentation": [polygon],
    }
