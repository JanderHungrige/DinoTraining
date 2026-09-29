"""Safe, reversible fixes and the preparation state (doc 83)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.datasets.store import DatasetStore
from app.prep.fixes import (
    NoAuditError,
    exclude_copies,
    exclude_unreadable,
    excluded_paths,
    set_class_map,
    set_excluded,
)
from app.prep.state import load_state

router = APIRouter()

FixAction = Literal["exclude", "include", "exclude-copies", "exclude-unreadable", "set-class-map"]


class FixRequest(BaseModel):
    action: FixAction
    #: For "exclude" / "include": stored image paths, as the image listing reports them.
    paths: list[str] = Field(default_factory=list)
    #: For "set-class-map": class as written -> class to train it as, or null to leave it out.
    class_map: dict[str, str | None] = Field(default_factory=dict)


class PrepStateResponse(BaseModel):
    excluded: list[str]
    class_map: dict[str, str | None]


class FixResponse(BaseModel):
    changed: int
    state: PrepStateResponse


def _state(dataset_id: str) -> PrepStateResponse:
    return PrepStateResponse(
        excluded=excluded_paths(dataset_id), class_map=load_state(dataset_id).class_map
    )


def _require(dataset_id: str) -> None:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")


@router.get(
    "/datasets/{dataset_id}/prep-state",
    response_model=PrepStateResponse,
    summary="What has been excluded, and how classes will be read",
)
async def get_prep_state(dataset_id: str) -> PrepStateResponse:
    _require(dataset_id)
    return _state(dataset_id)


@router.post(
    "/datasets/{dataset_id}/fixes",
    response_model=FixResponse,
    summary="Apply a safe, reversible fix",
)
async def apply_fix(dataset_id: str, request: FixRequest) -> FixResponse:
    """Nothing is deleted: images are excluded (and can be included again), and classes are
    mapped for training rather than rewritten in the data."""
    _require(dataset_id)
    try:
        if request.action in ("exclude", "include"):
            changed, unknown = set_excluded(dataset_id, request.paths, request.action == "exclude")
            if unknown:
                raise HTTPException(
                    status_code=422,
                    detail=f"Not images of this dataset: {', '.join(unknown[:5])}",
                )
        elif request.action == "exclude-copies":
            changed = exclude_copies(dataset_id)
        elif request.action == "exclude-unreadable":
            changed = exclude_unreadable(dataset_id)
        else:
            changed = len(set_class_map(dataset_id, request.class_map).class_map)
    except NoAuditError:
        raise HTTPException(
            status_code=409, detail="Audit this dataset first: the fix uses its findings."
        ) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return FixResponse(changed=changed, state=_state(dataset_id))


__all__ = ["router"]
