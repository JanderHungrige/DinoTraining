"""Decoding a video into a dataset's frames, as a job (doc 73).

A job rather than a request for the same reason doc 68's prepass is one: a few hundred
frames of 1080p take long enough that a request would time out while the work carried on
behind it, and the Generator wants to show progress while it waits.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.datasets.store import DatasetStore, dataset_dir
from app.ml.video.decode import VideoReadError, probe
from app.ml.video.extract import ExtractConfig, ExtractJob, frames_dir, get_extractor

logger = logging.getLogger(__name__)
router = APIRouter()


class ExtractRequest(BaseModel):
    source: str = Field(min_length=1, description="Absolute path to a video file.")
    dataset_id: str = Field(min_length=1, description="The frames are stored in this dataset.")
    start: int = Field(default=0, ge=0)
    #: Capped for the same reason doc 68 caps a prepass: 20,000 frames of 1080p is ~5 GB,
    #: which nobody should discover by pressing Start. A second range is one more click.
    count: int = Field(default=60, ge=1, le=20000)
    stride: int = Field(default=1, ge=1, le=1000)


class ExtractedFrame(BaseModel):
    #: The frame's number in the video, counting from zero.
    index: int
    path: str


class ExtractResponse(BaseModel):
    job_id: str
    state: str
    done: int
    total: int
    message: str
    frames: list[ExtractedFrame] = Field(default_factory=list)


def _describe(job: ExtractJob) -> ExtractResponse:
    frames = list(job.frames)
    return ExtractResponse(
        job_id=job.job_id,
        state=job.state,
        done=len(frames),
        total=job.total,
        message=job.message,
        frames=[ExtractedFrame(index=index, path=path) for index, path in frames],
    )


@router.post(
    "/video/extract",
    response_model=ExtractResponse,
    status_code=202,
    summary="Decode a range of a video's frames into a dataset",
)
async def start_extract(request: ExtractRequest) -> ExtractResponse:
    if not DatasetStore().exists(request.dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {request.dataset_id}")
    try:
        config = ExtractConfig(
            source=request.source,
            start=request.start,
            count=request.count,
            stride=request.stride,
        )
        info = probe(request.source)
        job = get_extractor().submit(
            config, frames_dir(dataset_dir(request.dataset_id), request.source), info.frames
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except VideoReadError as error:
        # A ValueError too, so it is caught here first: 415 says "not a video I can read",
        # which the 422 below would blur into "your numbers are wrong".
        raise HTTPException(status_code=415, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return _describe(job)


@router.get(
    "/video/extract/{job_id}",
    response_model=ExtractResponse,
    summary="Progress of a frame extraction, and the frames written so far",
)
async def get_extract(job_id: str) -> ExtractResponse:
    job = get_extractor().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No such extraction: {job_id}")
    return _describe(job)


@router.delete("/video/extract/{job_id}", summary="Stop an extraction, keeping its frames")
async def cancel_extract(job_id: str) -> ExtractResponse:
    extractor = get_extractor()
    job = extractor.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No such extraction: {job_id}")
    extractor.cancel(job_id)
    return _describe(job)


__all__ = ["router"]
