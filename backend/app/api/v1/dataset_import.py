"""Importing any dataset folder or video (doc 136): detect, import as a job, profile."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.datasets.intake.detect import Detection, scan
from app.datasets.intake.importer import ImportResult
from app.datasets.intake.jobs import ImportJob, get_import_jobs
from app.datasets.intake.profile import DatasetProfile, dataset_profile
from app.datasets.store import DatasetNotFoundError, DatasetStore

logger = logging.getLogger(__name__)
router = APIRouter()


class DetectRequest(BaseModel):
    path: str = Field(min_length=1, description="A dataset folder, or a video file.")


class ImportRequest(BaseModel):
    path: str = Field(min_length=1)
    name: str = Field(default="", max_length=200, description="Empty: the folder's name.")
    description: str | None = Field(default=None, max_length=4000)
    copy_images: bool = Field(
        default=False, description="Copy pictures into the app's data folder (else referenced)."
    )


class ImportJobView(BaseModel):
    job_id: str
    path: str
    state: Literal["running", "complete", "failed"]
    done: int
    total: int
    current: str
    result: ImportResult | None
    error: str | None


def _view(job: ImportJob) -> ImportJobView:
    return ImportJobView(
        job_id=job.job_id,
        path=job.path,
        state=job.state,
        done=job.done,
        total=job.total,
        current=job.current,
        result=job.result,
        error=job.error,
    )


@router.post(
    "/datasets/import/detect",
    response_model=Detection,
    summary="What a folder or video holds, before importing it (writes nothing)",
)
async def detect(request: DetectRequest) -> Detection:
    try:
        detection, _documents, _listing = scan(Path(request.path))
    except ValueError as error:
        logger.info("Detection of %s rejected: %s", request.path, error)
        raise HTTPException(status_code=422, detail=str(error)) from error
    return detection


@router.post(
    "/datasets/import",
    response_model=ImportJobView,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Import a folder or video as a new dataset (runs in the background)",
)
async def start_import(request: ImportRequest) -> ImportJobView:
    path = Path(request.path).expanduser()
    if not path.exists():
        raise HTTPException(status_code=422, detail=f"Not found: {request.path}")
    job = get_import_jobs().submit(path, request.name, request.description, request.copy_images)
    return _view(job)


@router.get(
    "/datasets/import/jobs/{job_id}",
    response_model=ImportJobView,
    summary="An import's progress and result",
)
async def import_job(job_id: str) -> ImportJobView:
    job = get_import_jobs().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No import job {job_id}")
    return _view(job)


@router.get(
    "/datasets/{dataset_id}/profile",
    response_model=DatasetProfile,
    summary="A dataset's parameters: media, pictures, annotated, classes, annotation types",
)
async def profile(dataset_id: str) -> DatasetProfile:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"No dataset {dataset_id}")
    try:
        return dataset_profile(dataset_id)
    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
