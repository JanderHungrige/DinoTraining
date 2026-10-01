"""Every training knob a model honours, explained (doc 99). Read by the form and MCP."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.params import FAMILIES, ParameterSet, family_for

router = APIRouter()


class ChoiceInfo(BaseModel):
    value: str
    label: str


class ParameterInfo(BaseModel):
    key: str
    label: str
    term: str
    help: str
    default: bool | int | float | str
    why: str
    kind: str
    level: str
    minimum: float | None
    maximum: float | None
    choices: list[ChoiceInfo]
    #: True when a chosen recipe's value replaces this one (the split lives there).
    recipe_overrides: bool


class ParameterSetInfo(BaseModel):
    family: str
    title: str
    covers: str
    parameters: list[ParameterInfo]


def _describe(family: ParameterSet) -> ParameterSetInfo:
    return ParameterSetInfo(
        family=family.family,
        title=family.title,
        covers=family.covers,
        parameters=[
            ParameterInfo(**{**asdict(p), "choices": [asdict(c) for c in p.choices]})
            for p in family.parameters
        ],
    )


@router.get(
    "/training/parameters",
    response_model=list[ParameterSetInfo],
    summary="Every model family's training parameters, with explanation and default",
)
async def list_parameters() -> list[ParameterSetInfo]:
    return [_describe(family) for family in FAMILIES]


@router.get(
    "/training/parameters/{model_id}",
    response_model=ParameterSetInfo,
    summary="One model's training parameters: 'head', or a fine-tune id such as 'sam3'",
)
async def get_parameters(model_id: str) -> ParameterSetInfo:
    try:
        return _describe(family_for(model_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


__all__ = ["router"]
