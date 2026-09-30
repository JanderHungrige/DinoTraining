"""What each fine-tunable model needs, and whether a dataset meets it (doc 92)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.datasets.store import DatasetStore
from app.finetune.preflight import Readiness, preflight
from app.finetune.requirements import REQUIREMENTS, FinetuneRequirements, get_requirements

router = APIRouter()


class CheckRequest(BaseModel):
    finetune_id: str
    dataset_id: str
    recipe_id: str | None = None


@router.get(
    "/finetune/requirements",
    response_model=list[FinetuneRequirements],
    summary="Every fine-tunable model and what its training data must look like",
)
async def list_requirements() -> list[FinetuneRequirements]:
    return list(REQUIREMENTS)


@router.get(
    "/finetune/requirements/{finetune_id}",
    response_model=FinetuneRequirements,
    summary="What one model's training data must look like",
)
async def one(finetune_id: str) -> FinetuneRequirements:
    try:
        return get_requirements(finetune_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/finetune/check",
    response_model=Readiness,
    summary="Check a dataset (and recipe) against a model's requirements, before training",
)
def check_dataset(request: CheckRequest) -> Readiness:
    if not DatasetStore().exists(request.dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {request.dataset_id}")
    try:
        return preflight(request.finetune_id, request.dataset_id, request.recipe_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


__all__ = ["router"]
