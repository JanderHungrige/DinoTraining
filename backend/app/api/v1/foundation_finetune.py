"""Fine-tuning a foundation detector — the routes (doc 44).

Split from `foundation.py` when that file crossed 300 lines. The seam is honest rather
than arbitrary: everything here *writes* a new model, everything there *reads* the
catalogue. They share one router, so the URL space is unchanged.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ml.foundation.finetune import FinetuneConfig
from app.ml.foundation.finetune_runner import get_finetune_runner
from app.ml.foundation.registry import get_foundation

logger = logging.getLogger(__name__)

router = APIRouter()


class FinetuneRequest(BaseModel):
    foundation_id: str = Field(min_length=1)
    dataset_ids: list[str] = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)
    epochs: int = Field(default=10, ge=1, le=200)
    learning_rate: float = Field(default=1e-4, gt=0, le=1.0)
    val_fraction: float = Field(default=0.2, ge=0.0, lt=1.0)
    unfreeze_blocks: int = Field(
        default=0,
        ge=-1,
        le=48,
        description=(
            "How many of the backbone's last blocks to train too (doc 55). 0 keeps it "
            "frozen; -1 trains all of it. Safe here because the whole model is saved."
        ),
    )


class FinetuneEpochInfo(BaseModel):
    epoch: int
    train_loss: float
    metrics: dict[str, float]


class FinetuneJobInfo(BaseModel):
    job_id: str
    state: str
    epoch: int
    total_epochs: int
    best_metric: float | None
    class_names: list[str]
    #: Proof the backbone was actually frozen. A silent no-op here looks exactly like a
    #: slow success, so the split is reported rather than only logged.
    frozen_parameters: int
    trainable_parameters: int
    message: str
    instance_id: str | None
    history: list[FinetuneEpochInfo]


def _describe_job(job: object) -> FinetuneJobInfo:
    return FinetuneJobInfo(
        job_id=job.job_id,  # type: ignore[attr-defined]
        state=job.state,  # type: ignore[attr-defined]
        epoch=job.epoch,  # type: ignore[attr-defined]
        total_epochs=job.total_epochs,  # type: ignore[attr-defined]
        best_metric=job.best_metric,  # type: ignore[attr-defined]
        class_names=list(job.class_names),  # type: ignore[attr-defined]
        frozen_parameters=job.frozen_parameters,  # type: ignore[attr-defined]
        trainable_parameters=job.trainable_parameters,  # type: ignore[attr-defined]
        message=job.message,  # type: ignore[attr-defined]
        instance_id=job.instance_id,  # type: ignore[attr-defined]
        history=[
            FinetuneEpochInfo(epoch=e.epoch, train_loss=e.train_loss, metrics=e.metrics)
            for e in job.history  # type: ignore[attr-defined]
        ],
    )


@router.post(
    "/foundation/finetune",
    response_model=FinetuneJobInfo,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Fine-tune a detector on your own datasets",
)
async def start_finetune(request: FinetuneRequest) -> FinetuneJobInfo:
    """Freeze the DINOv2 backbone, train the projector and decoder.

    Accepted rather than created: the run takes minutes, so the caller polls. Everything
    that can be wrong about the *request* is rejected here; everything that can go wrong
    during the run lands on the job.
    """
    try:
        config = FinetuneConfig(
            foundation_id=request.foundation_id,
            dataset_ids=tuple(request.dataset_ids),
            name=request.name,
            epochs=request.epochs,
            learning_rate=request.learning_rate,
            val_fraction=request.val_fraction,
            unfreeze_blocks=request.unfreeze_blocks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    if get_foundation(request.foundation_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown foundation model: {request.foundation_id}"
        )

    return _describe_job(get_finetune_runner().submit(config))


@router.get(
    "/foundation/finetune/{job_id}",
    response_model=FinetuneJobInfo,
    summary="Progress of one fine-tune",
)
async def read_finetune(job_id: str) -> FinetuneJobInfo:
    job = get_finetune_runner().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
    return _describe_job(job)


@router.post(
    "/foundation/finetune/{job_id}/cancel",
    response_model=FinetuneJobInfo,
    summary="Stop a fine-tune, keeping its best epoch",
)
async def cancel_finetune(job_id: str) -> FinetuneJobInfo:
    runner = get_finetune_runner()
    job = runner.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
    runner.cancel(job_id)
    return _describe_job(job)
