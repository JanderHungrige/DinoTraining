"""Prescan routes (doc 53) — find the images worth annotating before annotating any.

Under `/generate` rather than `/annotate` because it produces *no annotations*: it reports
which images a model has an opinion about, and the store never hears from it.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ml.annotators.prescan import DEFAULT_SCORE_THRESHOLD, PrescanConfig, PrescanKind
from app.ml.annotators.prescan_runner import PrescanJob, get_prescan_runner

logger = logging.getLogger(__name__)
router = APIRouter()

#: A scan is one forward pass per image. Beyond this the user should point at a folder, not
#: a disk — and the cap is here rather than in the runner so the refusal is immediate.
MAX_IMAGES = 5000


class PrescanRequest(BaseModel):
    kind: PrescanKind
    image_paths: list[str] = Field(min_length=1, max_length=MAX_IMAGES)
    labels: list[str] = Field(
        default_factory=list,
        description="What to look for. Empty means any detection counts.",
    )
    score_threshold: float = Field(default=DEFAULT_SCORE_THRESHOLD, ge=0.0, le=1.0)
    model_id: str = ""
    prompt: str = ""
    text_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    backbone_id: str = ""
    instance_id: str = ""
    foundation_id: str = ""
    concept: str = ""


class PrescanHitInfo(BaseModel):
    path: str
    boxes: int
    best_score: float
    labels: list[str]


class PrescanJobInfo(BaseModel):
    job_id: str
    state: str
    scanned: int
    total: int
    #: Images that would not open. Reported so a scan that read almost nothing cannot pass
    #: for a scan that found almost nothing.
    unreadable: int
    hits: list[PrescanHitInfo]
    message: str


def _describe(job: PrescanJob) -> PrescanJobInfo:
    scanned, unreadable, hits = job.snapshot()
    return PrescanJobInfo(
        job_id=job.job_id,
        state=job.state,
        scanned=scanned,
        total=job.total,
        unreadable=unreadable,
        hits=[
            PrescanHitInfo(
                path=hit.path,
                boxes=hit.boxes,
                best_score=hit.best_score,
                labels=list(hit.labels),
            )
            for hit in hits
        ],
        message=job.message,
    )


@router.post(
    "/generate/prescan",
    response_model=PrescanJobInfo,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Scan a list of images for the labels you care about",
)
async def start_prescan(request: PrescanRequest) -> PrescanJobInfo:
    """Start a scan. Returns immediately; poll for progress.

    Four hundred frames is minutes, so this cannot be a request that waits.
    """
    try:
        config = PrescanConfig(
            kind=request.kind,
            image_paths=tuple(request.image_paths),
            labels=tuple(label for label in request.labels if label.strip()),
            score_threshold=request.score_threshold,
            model_id=request.model_id,
            prompt=request.prompt,
            text_threshold=request.text_threshold,
            backbone_id=request.backbone_id,
            instance_id=request.instance_id,
            foundation_id=request.foundation_id,
            concept=request.concept,
        )
    except ValueError as exc:
        logger.warning("Rejected prescan: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return _describe(get_prescan_runner().submit(config))


@router.get(
    "/generate/prescan/{job_id}",
    response_model=PrescanJobInfo,
    summary="Progress and hits so far",
)
async def read_prescan(job_id: str) -> PrescanJobInfo:
    job = get_prescan_runner().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No prescan job {job_id}")
    return _describe(job)


@router.post(
    "/generate/prescan/{job_id}/cancel",
    response_model=PrescanJobInfo,
    summary="Stop a scan, keeping what it has found",
)
async def cancel_prescan(job_id: str) -> PrescanJobInfo:
    runner = get_prescan_runner()
    job = runner.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No prescan job {job_id}")
    runner.cancel(job_id)
    return _describe(job)


__all__ = ["MAX_IMAGES", "router"]
