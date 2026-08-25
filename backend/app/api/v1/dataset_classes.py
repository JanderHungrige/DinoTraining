"""A dataset's class vocabulary — what a box can be called (doc 60).

Split from `datasets.py` rather than added to it: that file is at 291 lines against the
project's 300-line gate, and the seam is the same one `generate_foundation.py` used —
everything here is about *names*, and nothing here reads or writes an annotation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.datasets.classes import MAX_CLASS_NAME, ClassInfo, ClassStore
from app.datasets.store import DatasetStore

logger = logging.getLogger(__name__)
router = APIRouter()


class ClassListResponse(BaseModel):
    classes: list[ClassInfo]


class CreateClassRequest(BaseModel):
    #: Bounded here as well as in `normalise`, so an oversized name is rejected by the
    #: schema before it reaches the store rather than only by the ValueError backstop.
    name: str = Field(min_length=1, max_length=MAX_CLASS_NAME)


def _require(dataset_id: str) -> None:
    """404 on an unknown dataset.

    The vocabulary of a dataset that does not exist is not an empty list — that reads as
    "this dataset has no classes yet" and would leave a typo'd id looking like a fresh
    dataset for as long as the user stared at it.
    """
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_id}")


@router.get(
    "/datasets/{dataset_id}/classes",
    response_model=ClassListResponse,
    summary="The classes a box in this dataset can be given",
)
async def list_classes(dataset_id: str) -> ClassListResponse:
    """Stored classes unioned with the ones already on a box.

    The union is what makes this work on a dataset that predates the table: a COCO import
    brings thirteen class names in as box prompts and writes no rows here.
    """
    _require(dataset_id)
    return ClassListResponse(classes=ClassStore().list_for(dataset_id))


@router.post(
    "/datasets/{dataset_id}/classes",
    response_model=ClassListResponse,
    summary="Create a class",
)
async def create_class(
    dataset_id: str, request: CreateClassRequest, response: Response
) -> ClassListResponse:
    """Add a class to the vocabulary and return the whole vocabulary back.

    Returning the full list rather than the one entry is deliberate: the caller is a picker
    that has to show every option anyway, and merging a single entry into a list it already
    holds is a second place for the ordering and the case rule to be implemented.

    **201 when it was new, 200 when it already existed.** Idempotent rather than a 409,
    because two reviewers creating `pedestrian` is not a conflict to resolve — the correct
    resolution is "you already have it", and a 409 would push that decision into the UI.
    """
    _require(dataset_id)
    store = ClassStore()
    try:
        created = store.create(dataset_id, request.name)
    except ValueError as error:
        # Below any specific handler, above nothing: a validation failure must never leave
        # here as a 500 with the reason only in the log. See CLAUDE.md.
        logger.info("Rejected class %r for %s: %s", request.name, dataset_id, error)
        raise HTTPException(status_code=422, detail=str(error)) from error

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return ClassListResponse(classes=store.list_for(dataset_id))


@router.delete(
    "/datasets/{dataset_id}/classes/{name}",
    response_model=ClassListResponse,
    summary="Remove a class from the vocabulary",
)
async def delete_class(dataset_id: str, name: str) -> ClassListResponse:
    """Remove a class. **Never touches a box.**

    A class forty annotations carry cannot be deleted out from under them — this removes
    the vocabulary row and nothing else, so the name keeps appearing in the listing as
    `stored: false` until those boxes are relabelled. Silently rewriting forty annotations
    is not something a picker's delete affordance should be able to do.

    404 for a name that was only ever inferred from a box: there was no row to remove, and
    reporting success would claim an effect that did not happen.
    """
    _require(dataset_id)
    store = ClassStore()
    if not store.delete(dataset_id, name):
        raise HTTPException(
            status_code=404,
            detail=f"{name!r} is not a stored class in this dataset.",
        )
    return ClassListResponse(classes=store.list_for(dataset_id))
