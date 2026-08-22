"""Reading a third-party COCO detection export into the dataset store.

The shape HuggingFace and Roboflow exports unpack to: a directory per split, each holding
its images beside an ``_annotations.coco.json``. COCO's ``bbox`` is ``[x, y, w, h]`` in
absolute pixels from the top-left — the same convention :class:`Box` documents — so the
boxes are copied rather than converted, and there is no coordinate transform to get wrong.

**Classes are resolved by name, never by id.** Roboflow exports carry a placeholder
category at id 0 that no annotation references, so "skip category 0" looks like the right
rule — and it is, until it isn't: of the three reference datasets, ``thermal`` and ``chess``
have a placeholder at 0 while ``blood``'s id 0 is the real class ``platelets``. Filtering by
id would silently delete every platelet annotation and still report a successful import.
Resolving each annotation's ``category_id`` through the file's own ``categories`` list
costs nothing for an unreferenced category and cannot make that mistake.

Everything imported is ``positive`` with provenance ``imported``. A published dataset
asserts presence and nothing else; it has no equivalent of Wave 1's negative/unclear
verdicts, and inventing one would put a judgement in the store that nobody made.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.paths import ensure_within
from app.datasets.models import Box, ImageAnnotation
from app.datasets.store import DatasetStore

logger = logging.getLogger(__name__)

#: What every Roboflow/HuggingFace COCO export calls its annotation file.
COCO_FILENAME = "_annotations.coco.json"


@dataclass(frozen=True, slots=True)
class ImportSummary:
    """What an import actually put in the store.

    The skip counters are returned rather than logged because a lossy import that reports
    success is indistinguishable from a clean one at the call site.
    """

    images: int = 0
    boxes: int = 0
    class_names: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    skipped_images: int = 0
    skipped_boxes: int = 0


@dataclass(frozen=True, slots=True)
class LoadedSplit:
    """One ``_annotations.coco.json`` parsed into store-ready annotations."""

    source: str
    annotations: tuple[ImageAnnotation, ...] = ()
    skipped_images: int = 0
    skipped_boxes: int = 0


def normalise_class(name: str) -> str:
    """Match the vocabulary the trainer derives from a box's prompt.

    ``app.ml.training.samples`` lowercases and strips a trailing full stop before building
    class indices. Normalising here keeps the summary honest about what the trainer will
    see and makes that later step idempotent. Duplicated deliberately rather than imported:
    the dataset layer must not depend on the ML layer.
    """
    return name.strip().lower().rstrip(".")


def find_coco_files(directory: Path) -> list[Path]:
    """Annotation files in ``directory`` and its immediate subdirectories, sorted.

    One level deep, matching ``list_images`` (doc 17) and for the same reason: a recursive
    walk pointed at ``/`` would enumerate the user's whole disk.
    """
    if not directory.is_dir():
        raise ValueError(f"Not a folder: {directory}")

    found = [directory / COCO_FILENAME] if (directory / COCO_FILENAME).is_file() else []
    for entry in sorted(directory.iterdir()):
        if entry.is_dir() and (entry / COCO_FILENAME).is_file():
            found.append(entry / COCO_FILENAME)
    return found


def _require_list(payload: dict[str, Any], key: str, path: Path) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{path.name} has no '{key}' list")
    return value


def _category_names(payload: dict[str, Any], path: Path) -> dict[int, str]:
    names: dict[int, str] = {}
    for entry in _require_list(payload, "categories", path):
        name = normalise_class(str(entry.get("name", "")))
        if name:
            names[int(entry["id"])] = name
    if not names:
        raise ValueError(f"{path.name} declares no usable categories")
    return names


def _image_records(payload: dict[str, Any], path: Path) -> dict[int, tuple[str, int, int]]:
    """``image_id -> (file_name, width, height)``.

    Dimensions come from the file, not from opening the image: the file is the authority
    the boxes were written against, so if the two disagree it is the boxes that are wrong —
    and ``_boxes_for_image`` is what catches that.
    """
    records: dict[int, tuple[str, int, int]] = {}
    for entry in _require_list(payload, "images", path):
        width, height = int(entry.get("width", 0)), int(entry.get("height", 0))
        if width > 0 and height > 0 and entry.get("file_name"):
            records[int(entry["id"])] = (str(entry["file_name"]), width, height)
    return records


def _group_by_image(payload: dict[str, Any], path: Path) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for entry in _require_list(payload, "annotations", path):
        grouped.setdefault(int(entry["image_id"]), []).append(entry)
    return grouped


def _boxes_for_image(
    entries: list[dict[str, Any]],
    categories: dict[int, str],
    width: int,
    height: int,
) -> tuple[list[Box], int]:
    """Build boxes for one image; return them with the number skipped.

    A box is skipped, never clamped, when it is degenerate or reaches outside the frame.
    Clamping would invent a coordinate the dataset's author did not publish.
    """
    boxes: list[Box] = []
    skipped = 0
    for entry in entries:
        bbox = entry.get("bbox")
        name = categories.get(int(entry.get("category_id", -1)))
        if not isinstance(bbox, list) or len(bbox) != 4 or name is None:
            skipped += 1
            continue
        x, y, w, h = (float(value) for value in bbox)
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > width or y + h > height:
            skipped += 1
            continue
        boxes.append(
            Box(label="positive", provenance="imported", x=x, y=y, w=w, h=h, prompt=name)
        )
    return boxes, skipped


def load_split(coco_path: Path) -> LoadedSplit:
    """Parse one ``_annotations.coco.json`` into store-ready annotations."""
    try:
        payload = json.loads(coco_path.read_text())
    except json.JSONDecodeError as error:
        raise ValueError(f"{coco_path.name} is not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{coco_path.name} is not a COCO object")

    categories = _category_names(payload, coco_path)
    images = _image_records(payload, coco_path)
    grouped = _group_by_image(payload, coco_path)
    root = coco_path.parent

    annotations: list[ImageAnnotation] = []
    skipped_images = 0
    skipped_boxes = 0

    for image_id, (file_name, width, height) in sorted(images.items()):
        try:
            # Confined to the directory holding the COCO file: `file_name` is third-party
            # text, and "../../.ssh/id_rsa" must not become an image this app copies.
            image_path = ensure_within(root, root / file_name)
        except ValueError:
            logger.warning("Skipping %s — path escapes %s", file_name, root)
            skipped_images += 1
            continue
        if not image_path.is_file():
            skipped_images += 1
            continue

        boxes, skipped = _boxes_for_image(grouped.get(image_id, []), categories, width, height)
        skipped_boxes += skipped
        # Images with no boxes are kept: a background image is real supervision for a
        # detector, so dropping them would quietly change the dataset.
        annotations.append(
            ImageAnnotation(path=str(image_path), width=width, height=height, boxes=boxes)
        )

    return LoadedSplit(
        source=root.name,
        annotations=tuple(annotations),
        skipped_images=skipped_images,
        skipped_boxes=skipped_boxes,
    )


def import_coco_dataset(
    store: DatasetStore, name: str, directory: Path, copy_images: bool = False
) -> tuple[str, ImportSummary]:
    """Create a dataset from a COCO export and fill it. Returns its id and a summary.

    Writes through :meth:`DatasetStore.replace_image_boxes` rather than touching SQLite,
    so an imported dataset is indistinguishable from a hand-annotated one everywhere
    except its provenance — and every downstream feature works with no change.
    """
    coco_files = find_coco_files(directory)
    if not coco_files:
        raise ValueError(
            f"No {COCO_FILENAME} in {directory} or its subdirectories"
        )

    splits = [load_split(path) for path in coco_files]
    dataset = store.create(name=name, prompt=None, copy_images=copy_images)

    images = boxes = 0
    class_names: set[str] = set()
    for split in splits:
        for annotation in split.annotations:
            store.replace_image_boxes(dataset.id, annotation)
            images += 1
            boxes += len(annotation.boxes)
            class_names.update(box.prompt for box in annotation.boxes if box.prompt)

    summary = ImportSummary(
        images=images,
        boxes=boxes,
        class_names=tuple(sorted(class_names)),
        sources=tuple(split.source for split in splits),
        skipped_images=sum(split.skipped_images for split in splits),
        skipped_boxes=sum(split.skipped_boxes for split in splits),
    )
    logger.info(
        "Imported %d image(s), %d box(es), %d class(es) into %s",
        summary.images,
        summary.boxes,
        len(summary.class_names),
        dataset.id,
    )
    return dataset.id, summary
