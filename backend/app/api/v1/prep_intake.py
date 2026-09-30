"""Checking a published dataset before import (doc 82)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.prep.intake import IntakeReport, inspect_coco

logger = logging.getLogger(__name__)
router = APIRouter()


class InspectRequest(BaseModel):
    directory: str = Field(min_length=1, description="Folder holding the COCO export.")


@router.post(
    "/datasets/import/coco/inspect",
    response_model=IntakeReport,
    summary="Check a COCO export before importing it (writes nothing)",
)
async def inspect_export(request: InspectRequest) -> IntakeReport:
    """Every failure here is bad input, a missing folder or unreadable JSON, so 422."""
    try:
        return inspect_coco(Path(request.directory).expanduser())
    except ValueError as error:
        logger.info("COCO inspection of %s rejected: %s", request.directory, error)
        raise HTTPException(status_code=422, detail=str(error)) from error


__all__ = ["router"]
