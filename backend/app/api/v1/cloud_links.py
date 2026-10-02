"""Linking a dataset in cloud storage (doc 148): detect from its listing, then import."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.dataset_import import ImportJobView, view_job
from app.cloud.errors import CloudError
from app.cloud.linking import detect_link
from app.cloud.links import get_link
from app.datasets.intake.detect import Detection
from app.datasets.intake.jobs import get_import_jobs

logger = logging.getLogger(__name__)
router = APIRouter()


class LinkDetectRequest(BaseModel):
    connection_id: str = Field(min_length=1)
    bucket: str = Field(min_length=1, description="The bucket (S3, GCS) or container (Azure).")
    prefix: str = ""


class LinkDetection(BaseModel):
    link_id: str
    detection: Detection


class LinkRequest(BaseModel):
    link_id: str = Field(min_length=1)
    name: str = Field(default="", max_length=200)
    description: str | None = Field(default=None, max_length=4000)


@router.post(
    "/cloud/links/detect",
    response_model=LinkDetection,
    summary="What a bucket's dataset holds (fetches only its annotation files)",
)
def detect(request: LinkDetectRequest) -> LinkDetection:
    try:
        link, detection = detect_link(
            request.connection_id, request.bucket.strip(), request.prefix.strip()
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (CloudError, ValueError) as error:
        logger.info("Cloud detection in %s refused: %s", request.bucket, error)
        raise HTTPException(status_code=422, detail=str(error)) from error
    return LinkDetection(link_id=link.id, detection=detection)


@router.post(
    "/cloud/links",
    response_model=ImportJobView,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Link the detected dataset (runs in the background)",
)
def link(request: LinkRequest) -> ImportJobView:
    try:
        get_link(request.link_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return view_job(
        get_import_jobs().submit_link(request.link_id, request.name, request.description)
    )
