"""Dataset endpoints: create, list, annotate, count, import, export, delete."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.datasets.bbox_conventions import Convention
from app.datasets.coco import build_coco, write_coco
from app.datasets.coco_import import ImportOptions, import_coco_dataset
from app.datasets.masks import MaskStore
from app.datasets.models import (
    DatasetCounts,
    DatasetInfo,
    ImageAnnotation,
    ImageMaskAnnotation,
)
from app.datasets.store import DatasetNotFoundError, DatasetStore, dataset_dir

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateDatasetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    prompt: str | None = None
    copy_images: bool = Field(
        default=False,
        description="Copy images into the dataset instead of referencing them in place.",
    )


class DatasetListResponse(BaseModel):
    datasets: list[DatasetInfo]


class ExportResponse(BaseModel):
    path: str
    images: int
    annotations: int


class ImportCocoRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    directory: str = Field(min_length=1, description="Folder holding the COCO export.")
    copy_images: bool = Field(
        default=False,
        description="Copy images into the dataset instead of referencing them in place.",
    )
    #: Doc 82: how the export writes its boxes, as POST .../import/coco/inspect decided.
    box_convention: Convention = "xywh"
    #: Doc 82: written class name -> class to store it as (accepted spelling merges).
    class_map: dict[str, str] = Field(default_factory=dict)
    #: Doc 82: keep the export's train/valid/test folders as the stored split.
    keep_source_split: bool = False


class ImportResponse(BaseModel):
    """What the import actually stored.

    The skip counters are part of the response, not just the log: an import that quietly
    dropped half its boxes must not be indistinguishable from a clean one at the call site.
    """

    dataset_id: str
    name: str
    images: int
    boxes: int
    class_names: list[str]
    sources: list[str]
    skipped_images: int
    skipped_boxes: int


def _store() -> DatasetStore:
    return DatasetStore()


def _require(dataset_id: str) -> DatasetInfo:
    try:
        return _store().get(dataset_id)
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_id}") from None


@router.post(
    "/datasets",
    response_model=DatasetInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Create a dataset",
)
async def create_dataset(request: CreateDatasetRequest) -> DatasetInfo:
    return _store().create(request.name, request.prompt, request.copy_images)


@router.get("/datasets", response_model=DatasetListResponse, summary="List datasets")
async def list_datasets() -> DatasetListResponse:
    return DatasetListResponse(datasets=_store().list_all())


@router.get("/datasets/{dataset_id}", response_model=DatasetInfo, summary="Dataset detail")
async def get_dataset(dataset_id: str) -> DatasetInfo:
    return _require(dataset_id)


@router.delete("/datasets/{dataset_id}", summary="Delete a dataset")
async def delete_dataset(dataset_id: str) -> dict[str, bool | str]:
    if not _store().delete(dataset_id):
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_id}")
    return {"id": dataset_id, "removed": True}


@router.put(
    "/datasets/{dataset_id}/images",
    response_model=DatasetCounts,
    summary="Save one image's boxes (replaces any existing set)",
)
async def put_image(dataset_id: str, annotation: ImageAnnotation) -> DatasetCounts:
    try:
        return _store().replace_image_boxes(dataset_id, annotation)
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_id}") from None


@router.put(
    "/datasets/{dataset_id}/images/masks",
    response_model=DatasetCounts,
    summary="Save one image's segmentation masks (replaces any existing set)",
)
async def put_image_masks(
    dataset_id: str, annotation: ImageMaskAnnotation
) -> DatasetCounts:
    try:
        return MaskStore().replace_image_masks(dataset_id, annotation)
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_id}") from None
    except ValueError as exc:
        # Backstop below the specific clauses: a mask with no foreground, or any future
        # raise site in the RLE path, is caller error and must not escape as a 500 with the
        # reason visible only in the log.
        logger.warning("Rejected masks for dataset %s: %s", dataset_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None


class DatasetFolder(BaseModel):
    """Where a dataset's pictures actually are on disk (doc 59)."""

    folder: str
    #: False when the folder no longer exists — an original the user moved or deleted.
    #: Reported rather than hidden, so the button can say why it will not open.
    exists: bool
    #: True when the store holds copies. False means the paths point at the user's own
    #: files, wherever those are, and opening the folder shows *their* directory.
    copies: bool


@router.get(
    "/datasets/{dataset_id}/folder",
    response_model=DatasetFolder,
    summary="The folder holding a dataset's images",
)
async def dataset_folder(dataset_id: str) -> DatasetFolder:
    """The directory to reveal in the OS file manager.

    **Derived from the first image, not from the dataset id.** Every dataset gets a
    `<store>/<id>/images/` directory at creation, but it only *contains* anything when the
    dataset was created with `copy_images`. For a dataset that references the user's own
    files, that directory is empty and opening it would show them nothing — the pictures
    are wherever they put them.

    Falls back to the dataset's own directory when there are no images at all, because a
    button that opens nothing is worse than one that opens the manifest.
    """
    info = _require(dataset_id)
    images = _store().image_annotations(dataset_id)
    if images:
        folder = Path(images[0][1]).parent
    else:
        folder = dataset_dir(dataset_id)

    return DatasetFolder(
        folder=str(folder), exists=folder.is_dir(), copies=info.copy_images
    )


@router.get(
    "/datasets/{dataset_id}/counts",
    response_model=DatasetCounts,
    summary="Live annotation counters",
)
async def get_counts(dataset_id: str) -> DatasetCounts:
    _require(dataset_id)
    return _store().counts(dataset_id)


@router.post(
    "/datasets/import/coco",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import a COCO export as a new dataset",
)
async def import_coco(request: ImportCocoRequest) -> ImportResponse:
    """Create a dataset from a third-party COCO export and fill it.

    Every failure mode here is bad *input* — a path that is not a folder, a directory with
    no annotation file, malformed JSON — so they all arrive as ValueError and leave as 422.
    Letting one escape as a 500 would put the only usable explanation in the log.
    """
    try:
        dataset_id, summary = import_coco_dataset(
            _store(),
            name=request.name,
            directory=Path(request.directory).expanduser(),
            copy_images=request.copy_images,
            options=ImportOptions(
                convention=request.box_convention,
                class_map=request.class_map or None,
                keep_source_split=request.keep_source_split,
            ),
        )
    except ValueError as error:
        logger.info("COCO import from %s rejected: %s", request.directory, error)
        raise HTTPException(status_code=422, detail=str(error)) from error

    return ImportResponse(
        dataset_id=dataset_id,
        name=request.name,
        images=summary.images,
        boxes=summary.boxes,
        class_names=list(summary.class_names),
        sources=list(summary.sources),
        skipped_images=summary.skipped_images,
        skipped_boxes=summary.skipped_boxes,
    )


@router.post(
    "/datasets/{dataset_id}/export/coco",
    response_model=ExportResponse,
    summary="Write annotations.coco.json",
)
async def export_coco(dataset_id: str) -> ExportResponse:
    info = _require(dataset_id)
    store = _store()

    images = store.image_annotations(dataset_id)
    masks = MaskStore().image_masks(dataset_id)
    coco = build_coco(info.name, images, info.prompt, masks=masks)
    path = write_coco(dataset_dir(dataset_id), coco)

    logger.info("Exported COCO for %s (%d annotations)", dataset_id, len(coco["annotations"]))
    return ExportResponse(
        path=str(path),
        images=len(coco["images"]),
        annotations=len(coco["annotations"]),
    )
