"""What a dataset is annotated for (doc 104)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.datasets.annotation_targets import TARGETS, AnnotationTarget, load_target, save_target
from app.datasets.store import DatasetStore

router = APIRouter()


class TargetChoice(BaseModel):
    target: str


def _require(dataset_id: str) -> None:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")


@router.get(
    "/annotation-targets",
    response_model=list[AnnotationTarget],
    summary="What a dataset can be annotated for, and which layers each needs and why",
)
async def list_targets() -> list[AnnotationTarget]:
    return list(TARGETS)


@router.get(
    "/datasets/{dataset_id}/annotation-target",
    response_model=TargetChoice,
    summary="What this dataset is annotated for ('open' until set)",
)
async def get_dataset_target(dataset_id: str) -> TargetChoice:
    _require(dataset_id)
    return TargetChoice(target=load_target(dataset_id))


@router.put(
    "/datasets/{dataset_id}/annotation-target",
    response_model=TargetChoice,
    summary="Set what this dataset is annotated for",
)
async def put_dataset_target(dataset_id: str, choice: TargetChoice) -> TargetChoice:
    _require(dataset_id)
    try:
        return TargetChoice(target=save_target(dataset_id, choice.target))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


__all__ = ["router"]
