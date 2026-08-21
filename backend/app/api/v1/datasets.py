"""Dataset endpoints: create, list, annotate, count, import, export, delete."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.datasets.coco import build_coco, write_coco
from app.datasets.coco_import import import_coco_dataset
from app.datasets.masks import MaskStore
from app.datasets.models import (
    Box,
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


class DatasetImageInfo(BaseModel):
    """One image in a dataset, with the boxes it already carries.

    The boxes ride along rather than needing a call per image: picking a dataset as a
    source means "carry on working on this", so the review surface needs them the moment
    it opens, and fetching them one image at a time would put a request behind every press
    of the Next key. `image_annotations` has already loaded them to answer this query.
    """

    path: str
    width: int
    height: int
    boxes: list[Box]


class DatasetImagesResponse(BaseModel):
    dataset_id: str
    images: list[DatasetImageInfo]


@router.get(
    "/datasets/{dataset_id}/images",
    response_model=DatasetImagesResponse,
    summary="List the images in a dataset",
)
async def list_dataset_images(dataset_id: str) -> DatasetImagesResponse:
    """The images a dataset holds, so it can be used as a source (doc 50).

    Returns **stored paths**, which is what every other image route in this app consumes —
    a dataset created with `copy_images` points inside the store, and one created without
    points at wherever the user's files were. Both are absolute and both open the same way,
    so a caller never has to know which kind it is holding.
    """
    _require(dataset_id)
    return DatasetImagesResponse(
        dataset_id=dataset_id,
        images=[
            DatasetImageInfo(path=path, width=width, height=height, boxes=boxes)
            for _, path, width, height, boxes in _store().image_annotations(dataset_id)
        ],
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
