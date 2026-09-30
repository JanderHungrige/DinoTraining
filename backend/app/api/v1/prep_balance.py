"""Class imbalance: the recommended remedy and what each would do (doc 86)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.datasets.store import DatasetStore
from app.prep.balance_plan import BalancePlan, plan_balance
from app.prep.profiles import get_profile
from app.prep.state import load_state
from app.prep.stats import collect

router = APIRouter()


@router.get(
    "/datasets/{dataset_id}/balance",
    response_model=BalancePlan,
    summary="How unequal the classes are, and the recommended remedy",
)
async def get_balance(dataset_id: str, target: str) -> BalancePlan:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    try:
        profile = get_profile(target)
    except KeyError as error:
        raise HTTPException(status_code=422, detail=f"Unknown target: {target}") from error
    facts = collect(dataset_id, class_map=load_state(dataset_id).class_map)
    return plan_balance(facts, profile)


__all__ = ["router"]
