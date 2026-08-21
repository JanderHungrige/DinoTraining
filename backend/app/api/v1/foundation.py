"""Foundation-model endpoints: what is offered, and running one over an image.

Kept apart from `/inference` because the thing being run is different in kind, not just in
configuration. `/inference` composes a backbone pass with N heads; a foundation model *is*
the whole prediction. Both return the same `PredictionResponse`, which is what lets the
viewer and the overlay registry treat them alike.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.inference import PredictionResponse, describe
from app.core.paths import is_installed, resolve_model_dir
from app.ml.errors import ModelNotInstalledError
from app.ml.foundation.build import FoundationUnavailableError, build_foundation
from app.ml.foundation.detect import DEFAULT_SCORE_THRESHOLD, RfDetrModel
from app.ml.foundation.finetune import FinetuneConfig
from app.ml.foundation.finetune_runner import get_finetune_runner
from app.ml.foundation.instances import FoundationInstance, FoundationInstanceStore
from app.ml.foundation.registry import all_foundations, get_foundation
from app.ml.images import ImageReadError, read_image
from app.ml.registry import get_model

logger = logging.getLogger(__name__)
router = APIRouter()


class FoundationInfo(BaseModel):
    """One foundation model as the picker shows it."""

    id: str
    title: str
    description: str
    task: str
    render_hint: str
    model_id: str
    licence: str
    #: Surfaced here too, not only in the admin panel: the viewer is where a user meets a
    #: model they have already installed, and "may I use this output?" is asked there.
    non_commercial: bool
    installed: bool
    approx_size_mb: int


class FoundationListResponse(BaseModel):
    foundations: list[FoundationInfo]


class FoundationRunRequest(BaseModel):
    image_path: str = Field(min_length=1)
    foundation_id: str = Field(min_length=1)
    score_threshold: float = Field(
        default=DEFAULT_SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Detection only; a depth model has nothing to threshold.",
    )


def _describe(spec_id: str) -> FoundationInfo:
    spec = get_foundation(spec_id)
    if spec is None:  # pragma: no cover - callers iterate the registry
        raise FoundationUnavailableError(spec_id)
    model = get_model(spec.model_id)
    if model is None:
        # A foundation spec naming a model the catalogue does not have is a packaging
        # error, not user input. Loud rather than silently unlisted.
        raise RuntimeError(f"{spec.id} names unknown model {spec.model_id}")
    return FoundationInfo(
        id=spec.id,
        title=spec.title,
        description=spec.description,
        task=spec.task,
        render_hint=spec.render_hint,
        model_id=spec.model_id,
        licence=model.licence,
        non_commercial=model.non_commercial,
        installed=is_installed(resolve_model_dir(spec.model_id)),
        approx_size_mb=model.approx_size_mb,
    )


class FinetuneRequest(BaseModel):
    foundation_id: str = Field(min_length=1)
    dataset_ids: list[str] = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)
    epochs: int = Field(default=10, ge=1, le=200)
    learning_rate: float = Field(default=1e-4, gt=0, le=1.0)
    val_fraction: float = Field(default=0.2, ge=0.0, lt=1.0)


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


@router.get(
    "/foundation",
    response_model=FoundationListResponse,
    summary="Self-contained models that predict without a head",
)
async def list_foundations() -> FoundationListResponse:
    """Catalogue entries **and** the models the user fine-tuned, in one list.

    One list on purpose: a fine-tuned detector is picked, run and reviewed exactly like a
    downloaded one, and splitting them would make every consumer learn a distinction that
    changes nothing about how it is used.
    """
    entries = [_describe(spec.id) for spec in all_foundations()]
    for instance in FoundationInstanceStore().list_all():
        entries.append(_describe_instance(instance))
    return FoundationListResponse(foundations=entries)


def _describe_instance(instance: FoundationInstance) -> FoundationInfo:
    base = get_model(instance.base_model_id)
    return FoundationInfo(
        id=instance.id,
        title=instance.name,
        description=instance.summary,
        task="detection",
        render_hint="boxes",
        model_id=instance.base_model_id,
        # A fine-tune inherits its base model's licence: it *is* that model's weights,
        # moved. Training on your own data does not relicense someone else's checkpoint.
        licence=base.licence if base else "unknown",
        non_commercial=bool(base and base.non_commercial),
        # Always: the weights are on this machine because this machine made them.
        installed=True,
        approx_size_mb=0,
    )


@router.post(
    "/foundation/predict",
    response_model=PredictionResponse,
    summary="Run one foundation model over one image",
)
async def predict(request: FoundationRunRequest) -> PredictionResponse:
    """Run a foundation model and return the same shape a head would.

    Error ordering matters and is the same discipline as `/inference`:
    `ModelNotInstalledError` subclasses `LookupError`, so it is caught first or a 409
    ("download it") silently becomes a 404 ("no such thing").

    Image failures use the codes the rest of the API already uses — 404 for absent, 415
    for unreadable — rather than a third convention for the same two problems. The first
    version of this handler had neither, and a missing file reached the user as a 500:
    `FileNotFoundError` is an `OSError`, so it slipped past both the `LookupError` and the
    `ValueError` backstop that were supposed to make that impossible.
    """
    try:
        image, _ = read_image(request.image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    except ImageReadError as exc:
        # Subclasses ValueError, so it must precede the backstop below.
        raise HTTPException(status_code=415, detail=str(exc)) from None

    try:
        model = build_foundation(request.foundation_id)
        # The one place that asks *what kind* of model this is. Not an id→implementation
        # map — `build_foundation` remains the only one of those — but a capability check:
        # a detector takes a score threshold and a depth map has nothing to threshold, so
        # a uniform signature would mean one of them accepting an argument it ignores.
        prediction = (
            model.predict(image, request.score_threshold)
            if isinstance(model, RfDetrModel)
            else model.predict(image)
        )
    except ModelNotInstalledError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} is not installed — download it in Admin / Models first.",
        ) from None
    except FoundationUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        # Backstop: a new raise site downstream must not reach the user as a 500 with the
        # reason only in the log.
        logger.error("Foundation run rejected for %s: %s", request.foundation_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return describe(prediction)
