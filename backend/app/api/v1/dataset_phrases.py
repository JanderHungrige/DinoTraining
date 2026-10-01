"""A dataset's SAM 3 phrases, and whether each picture was checked for them (doc 103)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.datasets.completeness import completeness, mark_absent, unknown_pictures
from app.datasets.db import transaction
from app.datasets.phrase_status import fill_unchecked, set_status, statuses_for
from app.datasets.phrases import PhraseInfo, PhraseStore, PictureStatus, Status
from app.datasets.store import DatasetStore

router = APIRouter()


class NewPhrase(BaseModel):
    #: Comma-separated variations: "red car, crimson car" is one phrase with a variation.
    text: str = Field(min_length=1, max_length=400)
    #: The class it belongs to; defaults to the phrase itself.
    class_name: str | None = Field(default=None, max_length=100)
    #: Doc 115: an umbrella term over these classes ("screw" for m8 and m9).
    classes: list[str] | None = Field(default=None, max_length=50)


class PhraseChange(BaseModel):
    variants: list[str] | None = None
    #: "Not to be confused with": wordings that must not find this (doc 108).
    confusable: list[str] | None = None
    #: Doc 115: an umbrella term's classes, replaced.
    classes: list[str] | None = None


class StatusChange(BaseModel):
    path: str = Field(min_length=1)
    phrase: str = Field(min_length=1)
    #: "complete" (every instance marked), "absent" (none here), or null to clear.
    status: Status | None


def _require(dataset_id: str) -> None:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")


def _unprocessable(error: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


@router.get(
    "/datasets/{dataset_id}/phrases",
    response_model=list[PhraseInfo],
    summary="Every phrase (class names included), with variations, instances and statuses",
)
def list_phrases(dataset_id: str) -> list[PhraseInfo]:
    _require(dataset_id)
    return PhraseStore().list_for(dataset_id)


@router.post(
    "/datasets/{dataset_id}/phrases",
    response_model=PhraseInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Add a phrase; comma-separated text adds variations (merged into an existing one)",
)
def add_phrase(dataset_id: str, body: NewPhrase) -> PhraseInfo:
    _require(dataset_id)
    try:
        return PhraseStore().add(dataset_id, body.text, body.class_name, body.classes)
    except ValueError as error:
        raise _unprocessable(error) from error


@router.patch(
    "/datasets/{dataset_id}/phrases/{phrase_id}",
    response_model=PhraseInfo,
    summary="Replace a phrase's variations or confusable phrases",
)
def change_phrase(dataset_id: str, phrase_id: int, body: PhraseChange) -> PhraseInfo:
    _require(dataset_id)
    try:
        return PhraseStore().update(
            dataset_id, phrase_id, body.variants, body.confusable, body.classes
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise _unprocessable(error) from error


@router.delete(
    "/datasets/{dataset_id}/phrases/{phrase_id}",
    summary="Delete a phrase, its links and statuses (masks keep their class)",
)
def delete_phrase(dataset_id: str, phrase_id: int) -> dict[str, bool]:
    _require(dataset_id)
    if not PhraseStore().delete(dataset_id, phrase_id):
        raise HTTPException(status_code=404, detail=f"No such phrase: {phrase_id}")
    return {"removed": True}


@router.get(
    "/datasets/{dataset_id}/images/phrase-status",
    response_model=list[PictureStatus],
    summary="Which phrases one picture was checked for",
)
def get_statuses(dataset_id: str, path: str = Query(min_length=1)) -> list[PictureStatus]:
    _require(dataset_id)
    try:
        return statuses_for(dataset_id, path)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put(
    "/datasets/{dataset_id}/images/phrase-status",
    response_model=list[PictureStatus],
    summary="Mark a picture 'complete' or 'absent' for a phrase, or clear it (null)",
)
def put_status(dataset_id: str, body: StatusChange) -> list[PictureStatus]:
    _require(dataset_id)
    try:
        return set_status(dataset_id, body.path, body.phrase, body.status)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise _unprocessable(error) from error


class FillRequest(BaseModel):
    phrase: str = Field(min_length=1)


@router.post(
    "/datasets/{dataset_id}/phrase-status/fill",
    summary="The phrase is fully annotated: mark every unchecked picture complete or absent",
)
def fill(dataset_id: str, body: FillRequest) -> dict[str, int]:
    _require(dataset_id)
    try:
        return fill_unchecked(dataset_id, body.phrase)
    except ValueError as error:
        raise _unprocessable(error) from error


class ClassCompleteness(BaseModel):
    #: When the class came into existence in this dataset (doc 117).
    since: str
    #: Saved pictures never looked at for it: saved before it existed, not checked by hand.
    unknown: int


@router.get(
    "/datasets/{dataset_id}/completeness",
    response_model=dict[str, ClassCompleteness],
    summary="Per class: since when it exists, and how many saved pictures are unknown for it",
)
def get_completeness(dataset_id: str) -> dict[str, ClassCompleteness]:
    _require(dataset_id)
    with transaction() as connection:
        found = completeness(connection, dataset_id)
    return {name: ClassCompleteness.model_validate(info) for name, info in found.items()}


@router.get(
    "/datasets/{dataset_id}/completeness/unknown",
    response_model=list[str],
    summary="The saved pictures never looked at for one class (doc 117), by path",
)
def get_unknown(dataset_id: str, class_name: str = Query(min_length=1)) -> list[str]:
    _require(dataset_id)
    with transaction() as connection:
        return [path for _, path in unknown_pictures(connection, dataset_id, class_name)]


class ClassRequest(BaseModel):
    class_name: str = Field(min_length=1, max_length=100)


@router.post(
    "/datasets/{dataset_id}/completeness/absent",
    summary="The class does not occur in the pictures saved before it: mark them absent",
)
def post_absent(dataset_id: str, body: ClassRequest) -> dict[str, int]:
    _require(dataset_id)
    try:
        with transaction() as connection:
            return {"marked": mark_absent(connection, dataset_id, body.class_name)}
    except ValueError as error:
        raise _unprocessable(error) from error


__all__ = ["router"]
