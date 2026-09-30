"""Model cards (doc 120): one JSON with everything an application needs to use a model."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException

from app.mlops.card import card_for

router = APIRouter()


@router.get(
    "/cards/{kind}/{instance_id}",
    summary="A trained model's card: base model, classes, preprocessing, outputs, metrics",
)
def get_card(kind: Literal["heads", "finetuned"], instance_id: str) -> dict[str, Any]:
    try:
        return card_for(kind, instance_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


__all__ = ["router"]
