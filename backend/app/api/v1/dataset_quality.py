"""A dataset's annotation guideline and second look (doc 109)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.datasets.quality import (
    SecondLook,
    Verdict,
    draw_sample,
    load_second_look,
    read_guideline,
    record_verdict,
    write_guideline,
)
from app.datasets.store import DatasetStore

router = APIRouter()


class Guideline(BaseModel):
    text: str


class SampleRequest(BaseModel):
    share: float = Field(default=0.05, gt=0, le=1)
    seed: int = 7


class VerdictRequest(BaseModel):
    path: str = Field(min_length=1)
    #: "right": it looked right; "changed": it needed a change.
    verdict: Verdict


class SecondLookInfo(BaseModel):
    sample: list[str]
    verdicts: dict[str, Verdict]
    reviewed: int
    changed: int
    #: Share of the reviewed pictures that needed a change; None until one is reviewed.
    rate: float | None


def _require(dataset_id: str) -> None:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")


def _info(look: SecondLook) -> SecondLookInfo:
    reviewed = look.reviewed
    return SecondLookInfo(
        sample=look.sample,
        verdicts=look.verdicts,
        reviewed=reviewed,
        changed=look.changed,
        rate=look.changed / reviewed if reviewed else None,
    )


@router.get(
    "/datasets/{dataset_id}/guideline", response_model=Guideline, summary="The annotation guideline"
)
async def get_guideline(dataset_id: str) -> Guideline:
    _require(dataset_id)
    return Guideline(text=read_guideline(dataset_id))


@router.put(
    "/datasets/{dataset_id}/guideline", response_model=Guideline, summary="Replace the guideline"
)
async def put_guideline(dataset_id: str, body: Guideline) -> Guideline:
    _require(dataset_id)
    try:
        return Guideline(text=write_guideline(dataset_id, body.text))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/datasets/{dataset_id}/second-look",
    response_model=SecondLookInfo,
    summary="Draw a new random sample of annotated pictures to look at again",
)
async def start_second_look(dataset_id: str, body: SampleRequest) -> SecondLookInfo:
    _require(dataset_id)
    try:
        return _info(draw_sample(dataset_id, body.share, body.seed))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/datasets/{dataset_id}/second-look",
    response_model=SecondLookInfo,
    summary="The second look so far: how many needed a change",
)
async def get_second_look(dataset_id: str) -> SecondLookInfo:
    _require(dataset_id)
    look = load_second_look(dataset_id)
    if look is None:
        raise HTTPException(status_code=404, detail="No second look has been started.")
    return _info(look)


@router.put(
    "/datasets/{dataset_id}/second-look/verdict",
    response_model=SecondLookInfo,
    summary="Record whether a sampled picture looked right or needed a change",
)
async def put_verdict(dataset_id: str, body: VerdictRequest) -> SecondLookInfo:
    _require(dataset_id)
    try:
        return _info(record_verdict(dataset_id, body.path, body.verdict))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


__all__ = ["router"]
