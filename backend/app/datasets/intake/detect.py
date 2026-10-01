"""What a folder (or a video) holds, before anything is imported (doc 136).

Annotated formats are tried in order of how specific their signature is: OpenLABEL (a
top-level `openlabel`), COCO (`images` + `annotations` + `categories`), YOLO (`labels/`
text files), Pascal VOC (`<annotation>` XML). Without annotations it is pictures, or
video. The counts come from the same documents the import will read.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.datasets.bbox_conventions import Convention
from app.datasets.coco_import import normalise_class
from app.datasets.exchange.layout import find_export
from app.datasets.exchange.restore import load, pictures_dir
from app.datasets.intake.documents import (
    Document,
    camera_pictures,
    coco_documents,
    openlabel_documents,
)
from app.datasets.intake.voc import is_voc, voc_documents
from app.datasets.intake.walk import Listing, walk
from app.datasets.intake.yolo import is_yolo, yolo_documents
from app.ml.video.decode import looks_like_video
from app.prep.intake import _evidence, decide

Kind = Literal["images", "video", "coco", "yolo", "voc", "openlabel", "dinotraining"]
#: What the UI words (doc 111): pictures in no annotation file (`uncovered` says how
#: many), boxes that fit no convention clearly, no annotations at all, video frames.
Note = Literal[
    "uncovered",
    "ambiguous-convention",
    "no-annotations",
    "video-frames",
    # Doc 142: an export whose pictures are neither copied, beside it, nor where they were.
    "export-pictures-missing",
]


class Detection(BaseModel):
    path: str
    kind: Kind
    #: A name to offer: the folder's (or the video's) own.
    name: str
    pictures: int
    videos: int
    annotation_files: int
    #: Pictures an annotation file covers: imported as annotated (doc 117's "saved").
    annotated_pictures: int
    objects: int
    classes: list[str]
    annotation_types: list[str]
    splits: list[str]
    #: COCO only: the box convention the numbers support (doc 82); None if ambiguous.
    convention: Convention | None = None
    notes: list[Note]
    uncovered: int = 0


def scan(
    path: Path, listing: Listing | None = None
) -> tuple[Detection, list[Document], Listing | None]:
    """Detect, and keep what the import needs, so it never reads twice differently.

    `listing`: a bucket's, already made (doc 148); otherwise the folder is walked.
    """
    path = path.expanduser()
    if listing is None and path.is_file() and looks_like_video(path):
        return _video(path, [path], None), [], None
    export = find_export(path)
    if export is not None:
        return _export_detection(path, export), [], None
    listing = listing or walk(path)
    for documents, kind in _annotated(listing):
        if documents:
            if kind == "openlabel":
                listing = camera_pictures(listing)
            return _annotated_detection(path, kind, documents, listing), documents, listing
    if listing.pictures:
        detection = _plain(path, "images", listing)
        return detection, [], listing
    if listing.videos:
        return _video(path, listing.videos, listing), [], listing
    raise ValueError(
        f"No pictures, videos or annotation files found in {path}. Expected pictures (JPEG, "
        "PNG, …), a video, or a COCO, YOLO, Pascal VOC or OpenLABEL export."
    )


def _annotated(listing: Listing) -> list[tuple[list[Document], Kind]]:
    """Lazily, in order: a later format is only read when the earlier found nothing."""
    attempts: list[tuple[list[Document], Kind]] = []
    kinds: tuple[Kind, ...] = ("openlabel", "coco", "yolo", "voc")
    for kind in kinds:
        documents = _documents(kind, listing)
        attempts.append((documents, kind))
        if documents:
            break
    return attempts


def _documents(kind: str, listing: Listing) -> list[Document]:
    if kind == "openlabel":
        return openlabel_documents(listing.json_files)
    if kind == "coco":
        return coco_documents(listing.json_files, listing.root)
    if kind == "yolo":
        return yolo_documents(listing) if is_yolo(listing) else []
    return voc_documents(listing) if is_voc(listing) else []


def _annotated_detection(
    path: Path, kind: Kind, documents: list[Document], listing: Listing
) -> Detection:
    covered: set[Path] = set()
    classes: set[str] = set()
    types: set[str] = set()
    objects = 0
    boxes: list[tuple[list[float], int, int]] = []
    for document in documents:
        sizes = {}
        for image in document.payload["images"]:
            covered.add((document.root / str(image["file_name"])).resolve())
            sizes[image["id"]] = (int(image.get("width") or 0), int(image.get("height") or 0))
        # Classes that are used: Roboflow exports declare an unused placeholder (doc 31).
        names = {
            c.get("id"): normalise_class(str(c.get("name", "")))
            for c in document.payload["categories"]
        }
        for annotation in document.payload["annotations"]:
            objects += 1
            classes.add(names.get(annotation.get("category_id"), ""))
            if annotation.get("bbox"):
                types.add("boxes")
                width, height = sizes.get(annotation.get("image_id"), (0, 0))
                if len(boxes) < 2000 and width and height:
                    boxes.append(([float(v) for v in annotation["bbox"]], width, height))
            if annotation.get("segmentation"):
                types.add("masks")
    uncovered = [p for p in listing.pictures if p.resolve() not in covered]
    notes: list[Note] = ["uncovered"] if uncovered else []
    convention = decide(_evidence(boxes)) if kind == "coco" else "xywh"
    if kind == "coco" and convention is None:
        notes.append("ambiguous-convention")
    return Detection(
        path=str(path),
        kind=kind,
        name=path.name,
        pictures=len(covered) + len(uncovered),
        videos=len(listing.videos),
        annotation_files=len({d.named for d in documents}),
        annotated_pictures=len(covered),
        objects=objects,
        classes=sorted(c for c in classes if c),
        annotation_types=sorted(types),
        splits=sorted({d.split for d in documents if d.split}),
        convention=convention,
        notes=notes,
        uncovered=len(uncovered),
    )


def _plain(path: Path, kind: Kind, listing: Listing) -> Detection:
    return Detection(
        path=str(path),
        kind=kind,
        name=path.name,
        pictures=len(listing.pictures),
        videos=len(listing.videos),
        annotation_files=0,
        annotated_pictures=0,
        objects=0,
        classes=[],
        annotation_types=[],
        splits=[],
        notes=["no-annotations"],
    )


def _video(path: Path, videos: list[Path], listing: Listing | None) -> Detection:
    return Detection(
        path=str(path),
        kind="video",
        name=path.stem if path.is_file() else path.name,
        pictures=len(listing.pictures) if listing else 0,
        videos=len(videos),
        annotation_files=0,
        annotated_pictures=0,
        objects=0,
        classes=[],
        annotation_types=[],
        splits=[],
        notes=["video-frames"],
    )


def _export_detection(path: Path, export: Path) -> Detection:
    """Doc 142: a DinoTraining export, read from its own file; restored, not imported."""
    dump = load(export)
    tables = dump["tables"]
    images = tables.get("images", [])
    kinds = [kind for kind, table in (("boxes", "boxes"), ("masks", "masks")) if tables.get(table)]
    prompts = {
        row["prompt"]
        for key in ("boxes", "masks")
        for row in tables.get(key, [])
        if row.get("prompt")
    }
    classes = sorted({row["name"] for row in tables.get("dataset_classes", [])} | prompts)
    notes: list[Note] = (
        [] if pictures_dir(export, dump) is not None else ["export-pictures-missing"]
    )
    return Detection(
        path=str(path),
        kind="dinotraining",
        name=str(dump["dataset"].get("name") or path.name),
        pictures=len(images),
        videos=0,
        annotation_files=1,
        annotated_pictures=sum(1 for image in images if image.get("annotated_at")),
        objects=len(tables.get("boxes", [])) + len(tables.get("masks", [])),
        classes=classes,
        annotation_types=kinds,
        splits=sorted({image["split"] for image in images if image.get("split")}),
        notes=notes,
    )
