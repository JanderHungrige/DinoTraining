"""The model-input plan and "what the model sees" (doc 85)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.datasets.store import DatasetStore
from app.prep.input_plan import MAX_GRID, InputPlan, plan_input
from app.prep.input_preview import MAX_PREVIEWS, InputPreview, colours_for, render, sample
from app.prep.profiles import ModelProfile, get_profile
from app.prep.state import load_state
from app.prep.stats import DatasetFacts, collect

logger = logging.getLogger(__name__)
router = APIRouter()


class PreviewRequest(BaseModel):
    target: str
    #: Tiles along the long edge; None takes the plan's choice, 1 turns tiling off.
    grid: int | None = Field(default=None, ge=1, le=MAX_GRID)
    count: int = Field(default=6, ge=1, le=MAX_PREVIEWS)
    seed: int = 42


def _load(dataset_id: str, target: str) -> tuple[DatasetFacts, ModelProfile, dict[str, str | None]]:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    try:
        profile = get_profile(target)
    except KeyError as error:
        raise HTTPException(status_code=422, detail=f"Unknown target: {target}") from error
    class_map = load_state(dataset_id).class_map
    return collect(dataset_id, class_map=class_map), profile, class_map


@router.get(
    "/datasets/{dataset_id}/input-plan",
    response_model=InputPlan,
    summary="How the target model will see this dataset, and whether to tile",
)
async def get_input_plan(
    dataset_id: str,
    target: str,
    grid: int | None = Query(default=None, ge=1, le=MAX_GRID),
) -> InputPlan:
    facts, profile, _ = _load(dataset_id, target)
    return plan_input(facts, profile, grid)


@router.post(
    "/datasets/{dataset_id}/input-preview",
    response_model=InputPreview,
    summary="Sampled images exactly as the target model will get them",
)
def preview_input(dataset_id: str, request: PreviewRequest) -> InputPreview:
    # Sync on purpose: decoding a dozen large images is CPU work, and FastAPI runs a sync
    # handler in its thread pool instead of blocking the event loop.
    facts, profile, class_map = _load(dataset_id, request.target)
    plan = plan_input(facts, profile, request.grid)
    tiles = max(plan.tiling.columns, plan.tiling.rows) if plan.tiling.recommended else 1
    images, skipped = [], []
    for image in sample(facts, profile, request.count, request.seed):
        try:
            images.append(render(facts, profile, image, tiles, class_map))
        except (OSError, ValueError) as error:
            # A missing or broken file is the audit's finding; the preview shows the rest.
            logger.info("Preview skipped %s: %s", image.path, error)
            skipped.append(image.path)
    return InputPreview(plan=plan, colours=colours_for(facts), images=images, skipped=skipped)


__all__ = ["router"]
