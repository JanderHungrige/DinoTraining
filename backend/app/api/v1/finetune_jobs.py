"""Fine-tuning any foundation model through one runner (doc 93)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.finetune.adapter import FinetuneSettings
from app.finetune.runner import (
    FinetuneRefusedError,
    FinetuneRequest,
    FoundationFinetuneJob,
    get_foundation_finetune_runner,
)
from app.params import family_for

router = APIRouter()


class StartRequest(BaseModel):
    finetune_id: str = Field(description="From GET /finetune/requirements.")
    dataset_ids: list[str] = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)
    recipe_id: str | None = None
    #: Omitted → the model's own default from the catalogue (doc 99): SAM 3 takes 4
    #: rounds, a DINO backbone 1e-3, instead of one number for all.
    epochs: int | None = None
    learning_rate: float | None = None
    seed: int | None = None
    #: Every other catalogue parameter, e.g. {"unfreeze_blocks": 4} (doc 95) or
    #: {"box_jitter": 0.2}. Unknown keys are refused (422), never silently ignored.
    options: dict[str, float] = Field(default_factory=dict)

    def settings(self) -> FinetuneSettings:
        """Checked against the catalogue; `ValueError` names the parameter (→ 422)."""
        given: dict[str, object] = dict(self.options)
        for key in ("epochs", "learning_rate", "seed"):
            if (value := getattr(self, key)) is not None:
                given[key] = value
        resolved = family_for(self.finetune_id).resolve(given)
        return FinetuneSettings(
            epochs=int(resolved.pop("epochs")),
            learning_rate=float(resolved.pop("learning_rate")),
            seed=int(resolved.pop("seed")),
            options={k: float(v) for k, v in resolved.items()},
        )


class EpochInfo(BaseModel):
    epoch: int
    train_loss: float
    metrics: dict[str, float]


class JobInfo(BaseModel):
    job_id: str
    finetune_id: str
    state: str
    epoch: int
    total_epochs: int
    primary_metric: str
    best_metric: float | None
    #: 0 when no epoch beat the base model on validation (nothing is saved then).
    best_epoch: int
    #: The base model and the fine-tuned one, on the same held-out pictures.
    baseline_metrics: dict[str, float]
    final_metrics: dict[str, float]
    held_out: str
    history: list[EpochInfo]
    notes: list[str]
    message: str
    instance_id: str | None


def _describe(job: FoundationFinetuneJob) -> JobInfo:
    return JobInfo(
        job_id=job.job_id,
        finetune_id=job.request.finetune_id,
        state=job.state,
        epoch=job.epoch,
        total_epochs=job.request.settings.epochs,
        primary_metric=job.primary_metric,
        best_metric=job.best_metric,
        best_epoch=job.best_epoch,
        baseline_metrics=job.baseline_metrics,
        final_metrics=job.final_metrics,
        held_out=job.held_out,
        history=[EpochInfo(**vars(e)) for e in job.history],
        notes=job.notes,
        message=job.message,
        instance_id=job.instance_id,
    )


@router.post(
    "/finetune/jobs",
    response_model=JobInfo,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a fine-tune; refused (409) with the failed requirements named",
)
def start(request: StartRequest) -> JobInfo:
    try:
        job = get_foundation_finetune_runner().submit(
            FinetuneRequest(
                finetune_id=request.finetune_id,
                dataset_ids=tuple(request.dataset_ids),
                name=request.name,
                recipe_id=request.recipe_id,
                settings=request.settings(),
            )
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FinetuneRefusedError as error:  # before ValueError: it is one
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _describe(job)


@router.get("/finetune/jobs", response_model=list[JobInfo], summary="All fine-tune jobs")
async def list_jobs() -> list[JobInfo]:
    return [_describe(job) for job in get_foundation_finetune_runner().list_all()]


@router.get("/finetune/jobs/{job_id}", response_model=JobInfo, summary="One fine-tune job")
async def get_job(job_id: str) -> JobInfo:
    job = get_foundation_finetune_runner().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No such fine-tune job: {job_id}")
    return _describe(job)


@router.post("/finetune/jobs/{job_id}/cancel", summary="Cancel a fine-tune")
async def cancel(job_id: str) -> dict[str, bool]:
    return {"cancelled": get_foundation_finetune_runner().cancel(job_id)}


__all__ = ["router"]
