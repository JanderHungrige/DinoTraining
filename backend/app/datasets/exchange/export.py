"""Write a dataset's export into `<target>/v-rex/` (doc 142)."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.core.config import Settings
from app.datasets.coco import build_coco
from app.datasets.exchange.dump import counts, dump_dataset, to_json
from app.datasets.exchange.layout import (
    COCO_FILE,
    DATA_FILE,
    PICTURES_DIR,
    export_folder,
    relative,
    resolve,
    write_atomically,
)
from app.datasets.intake.profile import pending_paths
from app.datasets.masks import MaskStore
from app.datasets.store import DatasetStore

logger = logging.getLogger(__name__)


class ExportResult(BaseModel):
    folder: str
    pictures: int
    annotated: int
    objects: int
    pictures_copied: int
    written_at: str


def coco_document(dataset_id: str, root: Path | None, settings: Settings | None) -> dict[str, Any]:
    """Doc 31's COCO of the saved pictures, `file_name` relative to the pictures' folder."""
    store = DatasetStore(settings)
    info = store.get(dataset_id)
    pending = pending_paths(dataset_id, settings)
    images = [row for row in store.image_annotations(dataset_id) if row[1] not in pending]
    masks = [row for row in MaskStore(settings).image_masks(dataset_id) if row[1] not in pending]
    coco = build_coco(info.name, images, info.prompt, masks=masks)
    paths = {row[0]: row[1] for row in images}
    for image in coco["images"]:
        path = paths.get(image["id"])
        if path and root:
            image["file_name"] = relative(path, root)
    coco["info"]["file_names"] = "relative to the folder that holds v-rex/"
    return coco


def _copy_pictures(dump: dict[str, Any], root: Path, destination: Path) -> int:
    """Copy pictures not already there with the same size; returns how many were copied."""
    copied = 0
    for image in dump["tables"]["images"]:
        source = resolve(image["path"], root)
        target = resolve(image["path"], destination)
        if target.is_file() and source.is_file() and target.stat().st_size == source.stat().st_size:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    return copied


def export_dataset(
    dataset_id: str, target: Path, include_pictures: bool = False, settings: Settings | None = None
) -> ExportResult:
    """Write `v-rex.json` and `annotations.coco.json` (and the pictures, if asked)."""
    folder = export_folder(target.expanduser())
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ValueError(f"Cannot write to {target}: {error}") from error
    dump = dump_dataset(dataset_id, settings)
    root = Path(dump["pictures_root"]) if dump["pictures_root"] else None
    copied = 0
    if include_pictures and root is not None:
        copied = _copy_pictures(dump, root, folder / PICTURES_DIR)
    write_atomically(folder / COCO_FILE, to_json(coco_document(dataset_id, root, settings)))
    write_atomically(folder / DATA_FILE, to_json(dump))
    pictures, annotated, objects = counts(dump)
    logger.info("Exported %s to %s (%d pictures, %d copied)", dataset_id, folder, pictures, copied)
    return ExportResult(
        folder=str(folder),
        pictures=pictures,
        annotated=annotated,
        objects=objects,
        pictures_copied=copied,
        written_at=datetime.fromisoformat(dump["exported_at"]).isoformat(),
    )
