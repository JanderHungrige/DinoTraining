"""Import what `detect.scan` found into a new dataset (doc 136).

Annotated formats go through doc 31's COCO parser (`parse_split`), boxes and masks alike,
so an import is indistinguishable from a hand-annotated dataset except by provenance.
Pictures without annotations, and video frames, get an image row **without**
`annotated_at`: saved means complete (doc 117), and nobody has looked at them yet.

All or nothing: a failure deletes the half-made dataset rather than leaving one that looks
complete.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from app.cloud.pictures import picture_size
from app.core.config import Settings
from app.core.paths import ensure_within
from app.datasets.coco_import import ImportOptions, normalise_class, parse_split
from app.datasets.db import transaction
from app.datasets.exchange.layout import find_export
from app.datasets.exchange.restore import restore
from app.datasets.images import NEVER_SAVED, store_image_file
from app.datasets.intake.details import set_details
from app.datasets.intake.detect import Detection, scan
from app.datasets.intake.documents import Document
from app.datasets.intake.segmentation import masks_for_image
from app.datasets.intake.walk import Listing
from app.datasets.masks import MaskStore
from app.datasets.models import ImageMaskAnnotation
from app.datasets.store import DatasetStore, dataset_dir
from app.ml.video.decode import probe
from app.ml.video.extract import ExtractConfig, extract_frames, frames_dir

logger = logging.getLogger(__name__)

#: Frames per video at most; a longer video is sampled evenly (every n-th frame).
MAX_FRAMES_PER_VIDEO = 3000

Progress = Callable[[int, int, str], None]


class ImportResult(BaseModel):
    dataset_id: str
    name: str
    pictures: int
    annotated_pictures: int
    objects: int
    masks: int
    classes: list[str]
    skipped_pictures: int
    skipped_objects: int


def run_import(
    path: Path,
    name: str,
    description: str | None,
    copy_images: bool,
    progress: Progress = lambda _done, _total, _what: None,
    settings: Settings | None = None,
    listing: Listing | None = None,
) -> ImportResult:
    """`listing`: a bucket's (doc 148); its pictures are referenced at their cache paths."""
    detection, documents, listing = scan(path, listing)
    if detection.kind == "dinotraining":
        return _restore(path, name, description, progress, settings)
    store = DatasetStore(settings)
    dataset = store.create(
        name=name.strip() or detection.name, prompt=None, copy_images=copy_images
    )
    result = ImportResult(
        dataset_id=dataset.id,
        name=dataset.name,
        pictures=0,
        annotated_pictures=0,
        objects=0,
        masks=0,
        classes=[],
        skipped_pictures=0,
        skipped_objects=0,
    )
    try:
        covered = _import_documents(
            store, dataset.id, documents, detection, result, progress, settings
        )
        if listing is not None and detection.kind != "video":
            plain = [p for p in listing.pictures if str(p.resolve()) not in covered]
            _add_plain(dataset.id, plain, result, progress, settings)
        if detection.kind == "video":
            videos = [path.expanduser()] if path.is_file() else (listing.videos if listing else [])
            _import_videos(dataset.id, videos, result, progress, settings)
        set_details(dataset.id, description, str(path), detection, settings)
    except Exception:
        logger.exception("Import of %s failed; removing the half-made dataset %s", path, dataset.id)
        store.delete(dataset.id)
        raise
    return result


def _restore(
    path: Path, name: str, description: str | None, progress: Progress, settings: Settings | None
) -> ImportResult:
    """Doc 142: an export of this app goes back whole, ids remapped, nothing re-detected."""
    export = find_export(path.expanduser())
    assert export is not None  # scan found it
    progress(0, 1, export.name)
    restored = restore(export, name, settings)
    if description and description.strip():
        with transaction(settings) as connection:
            connection.execute(
                "UPDATE datasets SET description = ? WHERE id = ?",
                (description.strip(), restored.dataset_id),
            )
    progress(1, 1, export.name)
    return ImportResult(
        dataset_id=restored.dataset_id,
        name=restored.name,
        pictures=restored.pictures,
        annotated_pictures=restored.annotated_pictures,
        objects=restored.objects,
        masks=restored.masks,
        classes=restored.classes,
        skipped_pictures=0,
        skipped_objects=0,
    )


def _import_documents(
    store: DatasetStore,
    dataset_id: str,
    documents: list[Document],
    detection: Detection,
    result: ImportResult,
    progress: Progress,
    settings: Settings | None,
) -> set[str]:
    masks = MaskStore(settings)
    options = ImportOptions(convention=detection.convention or "xywh", keep_source_split=True)
    total = detection.pictures
    covered: set[str] = set()
    classes: set[str] = set()
    for document in documents:
        loaded = parse_split(
            document.payload, document.root, document.named, document.split, options
        )
        result.skipped_pictures += loaded.skipped_images
        result.skipped_objects += loaded.skipped_boxes
        by_path = _masks_by_path(document)
        for annotation in loaded.annotations:
            store.replace_image_boxes(dataset_id, annotation)
            image_masks = by_path.get(annotation.path, [])
            if image_masks:
                masks.replace_image_masks(
                    dataset_id,
                    ImageMaskAnnotation(
                        path=annotation.path,
                        width=annotation.width,
                        height=annotation.height,
                        masks=image_masks,
                    ),
                )
            covered.add(str(Path(annotation.path).resolve()))
            result.pictures += 1
            result.annotated_pictures += 1
            result.objects += len(annotation.boxes)
            result.masks += len(image_masks)
            classes.update(box.prompt for box in annotation.boxes if box.prompt)
            classes.update(mask.prompt for mask in image_masks if mask.prompt)
            progress(result.pictures, total, Path(annotation.path).name)
    result.classes = sorted(classes)
    return covered


def _masks_by_path(document: Document) -> dict[str, list]:  # type: ignore[type-arg]
    """Each picture's masks, keyed as `parse_split` keys its pictures (the confined path)."""
    payload = document.payload
    names = {int(c["id"]): normalise_class(str(c.get("name", ""))) for c in payload["categories"]}
    grouped: dict[int, list[dict]] = {}  # type: ignore[type-arg]
    for entry in payload["annotations"]:
        if entry.get("segmentation"):
            grouped.setdefault(int(entry["image_id"]), []).append(entry)
    found = {}
    for image in payload["images"]:
        entries = grouped.get(int(image["id"]))
        width, height = int(image.get("width") or 0), int(image.get("height") or 0)
        if not entries or not width or not height:
            continue
        try:
            path = ensure_within(document.root, document.root / str(image["file_name"]))
        except ValueError:
            continue
        found[str(path)] = masks_for_image(entries, names, width, height)
    return found


def _add_plain(
    dataset_id: str,
    pictures: list[Path],
    result: ImportResult,
    progress: Progress,
    settings: Settings | None,
    sequence: str | None = None,
    indices: list[int] | None = None,
) -> None:
    """Image rows without `annotated_at`: in the dataset, not yet looked at."""
    directory = dataset_dir(dataset_id, settings)
    total = result.pictures + len(pictures)
    for start in range(0, len(pictures), 200):
        batch = pictures[start : start + 200]
        with transaction(settings) as connection:
            for offset, picture in enumerate(batch):
                try:
                    width, height = picture_size(picture)  # a bucket's: from its header
                except OSError:
                    result.skipped_pictures += 1
                    continue
                stored = store_image_file(directory, connection, dataset_id, str(picture))
                index = indices[start + offset] if indices else None
                connection.execute(
                    "INSERT INTO images (dataset_id, path, width, height, annotated_at,"
                    " sequence, frame_index) VALUES (?, ?, ?, ?, ?, ?, ?)"
                    " ON CONFLICT(dataset_id, path) DO NOTHING",
                    (dataset_id, stored, width, height, NEVER_SAVED, sequence, index),
                )
                result.pictures += 1
        progress(result.pictures, total, batch[-1].name)


def _frame_progress(progress: Progress, frames: int, name: str) -> Callable[[int, str], None]:
    """Bound per video: a lambda in the loop would report the last video's name."""
    return lambda index, _path: progress(index, frames, name)


def _import_videos(
    dataset_id: str,
    videos: list[Path],
    result: ImportResult,
    progress: Progress,
    settings: Settings | None,
) -> None:
    for video in videos:
        frames = max(probe(str(video)).frames, 1)
        stride = max(1, math.ceil(frames / MAX_FRAMES_PER_VIDEO))
        config = ExtractConfig(source=str(video), count=MAX_FRAMES_PER_VIDEO, stride=stride)
        destination = frames_dir(dataset_dir(dataset_id, settings), str(video))
        written = extract_frames(config, destination, _frame_progress(progress, frames, video.name))
        _add_plain(
            dataset_id,
            [Path(p) for _, p in written],
            result,
            progress,
            settings,
            sequence=str(video),
            indices=[i for i, _ in written],
        )
