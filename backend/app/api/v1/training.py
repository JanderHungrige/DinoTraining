"""Training: start, poll, cancel, and the live metrics stream.

SSE rather than WebSocket. Traffic is one-way, ``EventSource`` reconnects on its own,
and it is plain HTTP so no upgrade path is needed through the Tauri shell. A WebSocket
would add a second protocol for no capability this uses.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.ml.training.config import TrainingConfig
from app.ml.training.job import TrainingJob
from app.ml.training.runner import get_job_runner

logger = logging.getLogger(__name__)
router = APIRouter()

#: Seconds between polls of the in-memory job while streaming.
_POLL_SECONDS = 0.25
#: Idle seconds before a comment heartbeat, so intermediaries do not close a connection
#: that is simply between epochs — an epoch can take a while on CPU.
_HEARTBEAT_SECONDS = 15.0


class TrainingRequest(BaseModel):
    head_type_id: str
    backbone_id: str
    dataset_ids: list[str] = Field(min_length=1)
    epochs: int = Field(default=20, ge=1, le=1000)
    batch_size: int = Field(default=16, ge=1, le=512)
    learning_rate: float = Field(default=1e-3, gt=0, le=1.0)
    weight_decay: float = Field(default=0.01, ge=0)
    val_fraction: float = Field(default=0.2, ge=0, lt=1)
    test_fraction: float = Field(default=0.1, ge=0, lt=1)
    split_seed: int = 42
    save_best_only: bool = True
    early_stopping_patience: int = Field(default=5, ge=1)
    augment: bool = False

    def to_config(self) -> TrainingConfig:
        return TrainingConfig(
            head_type_id=self.head_type_id,
            backbone_id=self.backbone_id,
            dataset_ids=tuple(self.dataset_ids),
            epochs=self.epochs,
            batch_size=self.batch_size,
            learning_rate=self.learning_rate,
            weight_decay=self.weight_decay,
            val_fraction=self.val_fraction,
            test_fraction=self.test_fraction,
            split_seed=self.split_seed,
            save_best_only=self.save_best_only,
            early_stopping_patience=self.early_stopping_patience,
            augment=self.augment,
        )


class EpochInfo(BaseModel):
    epoch: int
    train_loss: float
    val_loss: float
    #: Open dict: keys are whatever the head type declared. Never hardcode them here or
    #: in the UI, or adding a head type silently empties the charts.
    metrics: dict[str, float]


class JobInfo(BaseModel):
    job_id: str
    state: str
    epoch: int
    total_epochs: int
    head_type_id: str
    backbone_id: str
    dataset_ids: list[str]
    class_names: list[str]
    skipped_mixed_class_images: int
    best_metric: float | None
    best_epoch: int | None
    primary_metric: str | None
    message: str
    head_instance_id: str | None
    history: list[EpochInfo]


class JobListResponse(BaseModel):
    jobs: list[JobInfo]


class CancelResponse(BaseModel):
    job_id: str
    cancelled: bool


def _describe(job: TrainingJob) -> JobInfo:
    from app.ml.heads.registry import get_head_type

    spec = get_head_type(job.config.head_type_id)
    return JobInfo(
        job_id=job.job_id,
        state=job.state,
        epoch=job.epoch,
        total_epochs=job.total_epochs,
        head_type_id=job.config.head_type_id,
        backbone_id=job.config.backbone_id,
        dataset_ids=list(job.config.dataset_ids),
        class_names=list(job.class_names),
        skipped_mixed_class_images=job.skipped_mixed_class_images,
        best_metric=job.best_metric,
        best_epoch=job.best_epoch,
        primary_metric=spec.primary_metric if spec else None,
        message=job.message,
        head_instance_id=job.head_instance_id,
        history=[
            EpochInfo(
                epoch=entry.epoch,
                train_loss=entry.train_loss,
                val_loss=entry.val_loss,
                metrics=entry.metrics,
            )
            for entry in job.history
        ],
    )


def _require_job(job_id: str) -> TrainingJob:
    job = get_job_runner().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown training job: {job_id}")
    return job


def _frame(event: str, payload: object) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.post(
    "/training/jobs",
    response_model=JobInfo,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a training run",
)
async def start_training(request: TrainingRequest) -> JobInfo:
    try:
        config = request.to_config()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    try:
        job = get_job_runner().submit(config)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        # 409, not 400: the request is well-formed, but the state of the world makes it
        # impossible — a depth head simply cannot be trained here.
        raise HTTPException(status_code=409, detail=str(exc)) from None

    logger.info("Started training job %s (%s)", job.job_id, config.head_type_id)
    return _describe(job)


@router.get("/training/jobs", response_model=JobListResponse, summary="List training jobs")
async def list_jobs() -> JobListResponse:
    return JobListResponse(jobs=[_describe(job) for job in get_job_runner().list_all()])


@router.get("/training/jobs/{job_id}", response_model=JobInfo, summary="Poll one job")
async def get_job(job_id: str) -> JobInfo:
    return _describe(_require_job(job_id))


@router.post(
    "/training/jobs/{job_id}/cancel", response_model=CancelResponse, summary="Cancel a job"
)
async def cancel_job(job_id: str) -> CancelResponse:
    _require_job(job_id)
    # False for an already-finished job is the truth, not an error: the caller wanted it
    # stopped and it is stopped.
    return CancelResponse(job_id=job_id, cancelled=get_job_runner().cancel(job_id))


async def _stream(job: TrainingJob, request: Request) -> AsyncIterator[str]:
    """Emit a snapshot, then each new epoch, then a terminal frame."""
    yield _frame("status", _describe(job).model_dump())

    sent_epochs = len(job.history)
    last_state = job.state
    idle = 0.0

    while True:
        if await request.is_disconnected():
            # Not an error. Training belongs to the runner, not to whoever was watching.
            logger.debug("Client disconnected from job %s stream", job.job_id)
            return

        emitted = False
        while sent_epochs < len(job.history):
            entry = job.history[sent_epochs]
            yield _frame(
                "epoch",
                {
                    "epoch": entry.epoch,
                    "train_loss": entry.train_loss,
                    "val_loss": entry.val_loss,
                    "metrics": entry.metrics,
                },
            )
            sent_epochs += 1
            emitted = True

        if job.state != last_state:
            last_state = job.state
            yield _frame("status", _describe(job).model_dump())
            emitted = True

        if job.finished:
            # The callback that saves the head runs in the worker thread and may land
            # just after the state flips; a short wait keeps head_instance_id out of the
            # UI's follow-up request rather than arriving as null.
            for _ in range(8):
                if job.head_instance_id is not None or job.best_state is None:
                    break
                await asyncio.sleep(_POLL_SECONDS)
            yield _frame("done", _describe(job).model_dump())
            return

        idle = 0.0 if emitted else idle + _POLL_SECONDS
        if idle >= _HEARTBEAT_SECONDS:
            yield ": ping\n\n"
            idle = 0.0

        await asyncio.sleep(_POLL_SECONDS)


@router.get("/training/jobs/{job_id}/events", summary="Live metrics stream (SSE)")
async def stream_job(job_id: str, request: Request) -> StreamingResponse:
    job = _require_job(job_id)
    return StreamingResponse(
        _stream(job, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Without this, a proxy that buffers will hold every frame until the run
            # ends, which is exactly the opposite of a live stream.
            "X-Accel-Buffering": "no",
        },
    )
