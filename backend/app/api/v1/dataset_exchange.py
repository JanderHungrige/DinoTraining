"""A dataset's complete export (doc 142) and where it goes (doc 143)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.datasets.exchange.export import ExportResult, export_dataset
from app.datasets.exchange.targets import (
    Target,
    TargetView,
    export_to_target,
    record,
    set_target,
    view,
)
from app.datasets.store import DatasetStore

logger = logging.getLogger(__name__)
router = APIRouter()


class ExportRequest(BaseModel):
    target: str = Field(
        min_length=1, description="The folder; the export goes into its dinotraining/."
    )
    include_pictures: bool = Field(
        default=False, description="Copy the pictures into the export too."
    )


def _require(dataset_id: str) -> None:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"No dataset {dataset_id}")


def _refused(dataset_id: str, error: Exception) -> HTTPException:
    # A target the user cannot write to is their input, not our failure (CLAUDE.md).
    logger.info("Export of %s refused: %s", dataset_id, error)
    return HTTPException(status_code=422, detail=str(error))


@router.post(
    "/datasets/{dataset_id}/export",
    response_model=ExportResult,
    summary="Export everything the dataset knows into <target>/dinotraining/ (import restores it)",
)
async def export(dataset_id: str, request: ExportRequest | None = None) -> ExportResult:
    """Without a body: to the stored target (doc 143). With one: there, and remembered."""
    _require(dataset_id)
    try:
        if request is None:
            return export_to_target(dataset_id)
        target = Target(
            kind="folder", folder=request.target, include_pictures=request.include_pictures
        )
        # Written first: a folder that cannot take the export is never remembered.
        result = export_dataset(dataset_id, Path(request.target), request.include_pictures)
        set_target(dataset_id, target)
        record(dataset_id, result)
        return result
    except (ValueError, OSError) as error:
        raise _refused(dataset_id, error) from error


@router.get(
    "/datasets/{dataset_id}/export/target",
    response_model=TargetView,
    summary="Where the dataset's export goes, what 'with the data' means here, and the last export",
)
async def get_target(dataset_id: str) -> TargetView:
    _require(dataset_id)
    return view(dataset_id)


@router.put(
    "/datasets/{dataset_id}/export/target",
    response_model=TargetView,
    summary="Choose where the dataset's export goes: with the data, or a folder",
)
async def put_target(dataset_id: str, target: Target) -> TargetView:
    _require(dataset_id)
    try:
        set_target(dataset_id, target)
    except ValueError as error:
        raise _refused(dataset_id, error) from error
    return view(dataset_id)
