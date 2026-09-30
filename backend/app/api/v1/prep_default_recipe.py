"""The default recipe for a model, in one call (doc 101)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.datasets.store import DatasetStore
from app.prep.default_recipe import make_default_recipe, profile_for
from app.prep.jobs import PrepJob, get_prep_runner
from app.prep.profiles import get_profile
from app.prep.recipe import Recipe

router = APIRouter()

KIND = "default-recipe"


class DefaultRecipeRequest(BaseModel):
    #: "head", or a fine-tune id from GET /finetune/requirements.
    model_id: str
    #: For "head": which head, on which backbone.
    head_type_id: str | None = None
    backbone_id: str | None = None


class TargetInfo(BaseModel):
    target: str
    label: str


class DefaultRecipeJob(BaseModel):
    job_id: str
    state: str
    #: The step running now, in plain words; the result or the refusal once finished.
    message: str
    recipe: Recipe | None = None


def _target(request: DefaultRecipeRequest) -> str:
    try:
        return profile_for(request.model_id, request.head_type_id, request.backbone_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _describe(job: PrepJob) -> DefaultRecipeJob:
    recipe = job.result if isinstance(job.result, Recipe) else None
    return DefaultRecipeJob(job_id=job.job_id, state=job.state, message=job.message, recipe=recipe)


@router.get(
    "/prep/targets/resolve",
    response_model=TargetInfo,
    summary="Which preparation profile a model trains with (for Prepare data)",
)
async def resolve_target(
    model_id: str, head_type_id: str | None = None, backbone_id: str | None = None
) -> TargetInfo:
    target = _target(
        DefaultRecipeRequest(model_id=model_id, head_type_id=head_type_id, backbone_id=backbone_id)
    )
    return TargetInfo(target=target, label=get_profile(target).label)


@router.post(
    "/datasets/{dataset_id}/recipes/default",
    response_model=DefaultRecipeJob,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Make the model's default recipe for a dataset: audit, split, recommendations (a job)",
)
async def create_default(dataset_id: str, request: DefaultRecipeRequest) -> DefaultRecipeJob:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    target = _target(request)
    job = get_prep_runner().submit(
        KIND, lambda job, progress: make_default_recipe(dataset_id, target, job, progress)
    )
    return _describe(job)


@router.get(
    "/prep/default-recipes/{job_id}",
    response_model=DefaultRecipeJob,
    summary="A default recipe's progress, and the recipe once saved",
)
async def get_default_job(job_id: str) -> DefaultRecipeJob:
    job = get_prep_runner().get(job_id)
    if job is None or job.kind != KIND:
        raise HTTPException(status_code=404, detail=f"No such default-recipe job: {job_id}")
    return _describe(job)


__all__ = ["router"]
