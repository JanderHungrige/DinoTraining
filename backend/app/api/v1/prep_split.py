"""The leak-free train/validation/test split (doc 84)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.datasets.store import DatasetStore
from app.prep.split_service import (
    SplitMode,
    SplitRefusedError,
    SplitReport,
    current_split,
    make_split,
)

router = APIRouter()


class SplitRequest(BaseModel):
    val_fraction: float = Field(default=0.2, ge=0.0, lt=1.0)
    test_fraction: float = Field(default=0.1, ge=0.0, lt=1.0)
    seed: int = 42
    #: "auto" groups scenes and video segments; "keep-source" keeps an imported split.
    mode: SplitMode = "auto"


def _require(dataset_id: str) -> None:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")


@router.post(
    "/datasets/{dataset_id}/split",
    response_model=SplitReport,
    summary="Split a dataset without leakage, and store the split",
)
async def split_dataset(dataset_id: str, request: SplitRequest) -> SplitReport:
    _require(dataset_id)
    try:
        return make_split(
            dataset_id, request.val_fraction, request.test_fraction, request.seed, request.mode
        )
    except ValueError as error:  # SplitRefusedError, and any other bad input
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get(
    "/datasets/{dataset_id}/split",
    response_model=SplitReport,
    summary="The split stored for a dataset",
)
async def get_split(dataset_id: str) -> SplitReport:
    _require(dataset_id)
    report = current_split(dataset_id)
    if report is None:
        raise HTTPException(status_code=404, detail="This dataset has not been split yet.")
    return report


__all__ = ["SplitRefusedError", "router"]
