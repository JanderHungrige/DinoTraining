"""COCO documents in memory: what every annotated format becomes before import (doc 136).

COCO files are read as they are. OpenLABEL (OSDaR23, doc 49) is converted per camera.
YOLO and Pascal VOC live in their own modules. Each yields `Document`s, and both the
detection and the import read the same documents, so what the preview promises is what
the import does.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from app.cloud.errors import CloudError
from app.cloud.pictures import picture_size
from app.datasets.coco_import import split_of
from app.datasets.intake.walk import Listing
from app.datasets.openlabel import camera_names, load_openlabel
from app.datasets.openlabel_to_coco import convert

logger = logging.getLogger(__name__)

#: Doc 49: OSDaR23's track is an open polyline to the horizon; as a box it would teach
#: "most of the image". The other formats publish what they mean and keep everything.
OPENLABEL_EXCLUDED = frozenset({"track"})
#: OpenLABEL cameras whose pictures a detector here can use (not lidar or radar).
_CAMERA_PREFIXES = ("rgb", "ir")


@dataclass(frozen=True)
class Document:
    """One COCO document; `file_name`s resolve against `root` and may not leave it."""

    payload: dict[str, Any]
    root: Path
    named: Path
    split: str | None


def is_coco(payload: object) -> bool:
    return isinstance(payload, dict) and all(
        isinstance(payload.get(key), list) for key in ("images", "annotations", "categories")
    )


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def coco_documents(json_files: list[Path], root: Path) -> list[Document]:
    """Every COCO file under the dataset folder, any name (Roboflow's or not)."""
    documents = []
    for path in json_files:
        payload = _read_json(path)
        if is_coco(payload):
            assert isinstance(payload, dict)
            documents.append(
                Document(
                    payload, path.parent, path, split_of(path.parent.name) or _split_in(path, root)
                )
            )
    return documents


def _split_in(path: Path, root: Path) -> str | None:
    """A split named anywhere between the dataset folder and the file."""
    for part in path.relative_to(root).parts[:-1]:
        split = split_of(part)
        if split:
            return split
    return None


def openlabel_documents(json_files: list[Path]) -> list[Document]:
    """OSDaR23-style OpenLABEL files: one document per file and picture camera."""
    documents = []
    for path in json_files:
        if not _mentions_openlabel(path):
            continue
        try:
            root = load_openlabel(path)
        except ValueError as error:
            logger.info("Skipping %s: %s", path, error)
            continue
        for camera in camera_names(root):
            if not camera.lower().startswith(_CAMERA_PREFIXES):
                continue
            payload, _summary = convert(root, camera, exclude=OPENLABEL_EXCLUDED)
            # A camera without one annotation is not annotated (doc 138): OSDaR23's side
            # cameras carry none, and "annotated, empty" would train their people and
            # signals as background. Their pictures arrive never saved instead.
            if not payload["annotations"]:
                continue
            fill_sizes(payload, path.parent)
            if payload["images"]:
                documents.append(Document(payload, path.parent, path, None))
    return documents


def camera_pictures(listing: Listing) -> Listing:
    """An OpenLABEL folder's pictures are its cameras' frames only (doc 138): OSDaR23
    ships its radar as PNG renderings, which would otherwise import as pictures."""

    def from_camera(path: Path) -> bool:
        folders = path.relative_to(listing.root).parts[:-1]
        return any(folder.lower().startswith(_CAMERA_PREFIXES) for folder in folders)

    return replace(listing, pictures=[path for path in listing.pictures if from_camera(path)])


def _mentions_openlabel(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return '"openlabel"' in handle.read(4096)
    except OSError:
        return False


def fill_sizes(payload: dict[str, Any], root: Path) -> None:
    """Width and height from the pictures themselves, where the document has none.

    Doc 31's importer drops an image without a size, and the OpenLABEL conversion writes
    none: without this, an OSDaR23 import would import nothing (found 2026-10-01). Only
    the header is read.

    A picture that is not there or cannot be opened is dropped here, with its annotations:
    the import would drop it anyway, and the detection's counts must say what will arrive
    (found 2026-10-01: OSDaR23's "RGB centre only" promised 90 pictures for its 10, because
    the labels name all nine cameras).
    """
    kept = []
    for image in payload.get("images", []):
        if not (image.get("width") and image.get("height")):
            try:
                image["width"], image["height"] = picture_size(root / str(image["file_name"]))
            except CloudError:
                raise  # the bucket could not be read: not the same as "no such picture"
            except (OSError, ValueError):
                logger.info("Cannot read the size of %s", image.get("file_name"))
                continue
        kept.append(image)
    ids = {image["id"] for image in kept}
    payload["images"] = kept
    payload["annotations"] = [
        entry for entry in payload.get("annotations", []) if entry["image_id"] in ids
    ]
