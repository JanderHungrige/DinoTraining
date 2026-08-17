"""Dataset endpoints: create, list, annotate, count, export, delete."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.datasets.coco import build_coco, write_coco
from app.datasets.models import DatasetCounts, DatasetInfo, ImageAnnotation
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


@router.get(
    "/datasets/{dataset_id}/counts",
    response_model=DatasetCounts,
    summary="Live annotation counters",
)
async def get_counts(dataset_id: str) -> DatasetCounts:
    _require(dataset_id)
    return _store().counts(dataset_id)


@router.post(
    "/datasets/{dataset_id}/export/coco",
    response_model=ExportResponse,
    summary="Write annotations.coco.json",
)
async def export_coco(dataset_id: str) -> ExportResponse:
    info = _require(dataset_id)
    store = _store()

    images = store.image_annotations(dataset_id)
    coco = build_coco(info.name, images, info.prompt)
    path = write_coco(dataset_dir(dataset_id), coco)

    logger.info("Exported COCO for %s (%d annotations)", dataset_id, len(coco["annotations"]))
    return ExportResponse(
        path=str(path),
        images=len(coco["images"]),
        annotations=len(coco["annotations"]),
    )
