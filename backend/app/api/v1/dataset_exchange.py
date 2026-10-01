"""A dataset's complete export (doc 142): everything it knows, to a folder of the user's."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.datasets.exchange.export import ExportResult, export_dataset
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


@router.post(
    "/datasets/{dataset_id}/export",
    response_model=ExportResult,
    summary="Export everything the dataset knows into <target>/dinotraining/ (import restores it)",
)
async def export(dataset_id: str, request: ExportRequest) -> ExportResult:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"No dataset {dataset_id}")
    try:
        return export_dataset(dataset_id, Path(request.target), request.include_pictures)
    except (ValueError, OSError) as error:
        # A target the user cannot write to is their input, not our failure (CLAUDE.md).
        logger.info("Export of %s to %s refused: %s", dataset_id, request.target, error)
        raise HTTPException(status_code=422, detail=str(error)) from error
