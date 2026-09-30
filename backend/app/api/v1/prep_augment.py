"""Augmentation presets: the recommendation and a live preview (doc 87)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.datasets.store import DatasetStore
from app.prep.augment_plan import (
    AugmentationPlan,
    AugmentationPreview,
    plan_augmentation,
    preview_augmentation,
)
from app.prep.profiles import ModelProfile, get_profile
from app.prep.state import load_state
from app.prep.stats import DatasetFacts, collect

logger = logging.getLogger(__name__)
router = APIRouter()


class AugmentationPreviewRequest(BaseModel):
    target: str
    preset: str
    count: int = Field(default=4, ge=1, le=8)
    seed: int = 42


def _load(dataset_id: str, target: str) -> tuple[DatasetFacts, ModelProfile]:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    try:
        profile = get_profile(target)
    except KeyError as error:
        raise HTTPException(status_code=422, detail=f"Unknown target: {target}") from error
    return collect(dataset_id, class_map=load_state(dataset_id).class_map), profile


@router.get(
    "/datasets/{dataset_id}/augmentation",
    response_model=AugmentationPlan,
    summary="The augmentation presets, and which one fits this dataset",
)
async def get_augmentation(dataset_id: str, target: str) -> AugmentationPlan:
    facts, profile = _load(dataset_id, target)
    return plan_augmentation(facts, profile)


@router.post(
    "/datasets/{dataset_id}/augmentation-preview",
    response_model=AugmentationPreview,
    summary="One picture as the model gets it, and changed versions of it",
)
def preview(dataset_id: str, request: AugmentationPreviewRequest) -> AugmentationPreview:
    # Sync: image decoding is CPU work and runs in FastAPI's thread pool.
    facts, profile = _load(dataset_id, request.target)
    try:
        return preview_augmentation(facts, profile, request.preset, request.count, request.seed)
    except OSError as error:
        logger.info("Augmentation preview failed for %s: %s", dataset_id, error)
        raise HTTPException(
            status_code=422, detail=f"The picture cannot be read: {error}"
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


__all__ = ["router"]
