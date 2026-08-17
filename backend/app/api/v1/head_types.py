"""Head types, and whether each one fits a given backbone.

The compatibility verdict carries a reason. Greying out a row without saying why leaves
the user with no way forward — which backbone should they download instead?
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.ml.backbone import read_capabilities
from app.ml.errors import ModelNotInstalledError
from app.ml.heads.registry import (
    HeadTask,
    HeadTypeSpec,
    RenderHint,
    all_head_types,
    check_compatibility,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class HeadTypeInfo(BaseModel):
    id: str
    task: HeadTask
    title: str
    description: str
    trainable: bool = Field(
        description="False means usable for inference but not fine-tunable here."
    )
    target_format: str | None
    consumes: str
    geometry: str = Field(description="center-crop, or aspect-preserve for dense tasks.")
    metrics: list[str]
    primary_metric: str | None
    primary_metric_mode: str | None
    render_hint: RenderHint
    compatible: bool | None = Field(
        default=None, description="Null unless ?backbone= was supplied."
    )
    incompatible_reason: str | None = None


class HeadTypeListResponse(BaseModel):
    head_types: list[HeadTypeInfo]


def _describe(spec: HeadTypeSpec) -> HeadTypeInfo:
    return HeadTypeInfo(
        id=spec.id,
        task=spec.task,
        title=spec.title,
        description=spec.description,
        trainable=spec.trainable,
        target_format=spec.target_format,
        consumes=spec.consumes,
        geometry=spec.geometry,
        metrics=list(spec.metrics),
        primary_metric=spec.primary_metric,
        primary_metric_mode=spec.primary_metric_mode,
        render_hint=spec.render_hint,
    )


@router.get(
    "/head-types",
    response_model=HeadTypeListResponse,
    summary="List head types, optionally with backbone compatibility",
)
async def list_head_types(
    backbone: str | None = Query(
        default=None, description="Registry id of an installed backbone to check against."
    ),
) -> HeadTypeListResponse:
    entries = [_describe(spec) for spec in all_head_types()]

    if backbone is None:
        return HeadTypeListResponse(head_types=entries)

    try:
        capabilities = read_capabilities(backbone)
    except ModelNotInstalledError:
        # 409 not 404: the backbone exists in the catalogue, it just has no config to
        # read yet. "Download it first" is a different fix from "that id is wrong".
        raise HTTPException(
            status_code=409, detail=f"{backbone} is not installed — download it first."
        ) from None
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Unknown backbone: {backbone}") from None
    except ValueError as exc:
        # Covers both "that is a detector, not a backbone" and a corrupt config. Both
        # already say which they are; wrapping them in a generic "unreadable config"
        # would mislabel the first one.
        logger.warning("Cannot read capabilities for %s: %s", backbone, exc)
        raise HTTPException(status_code=409, detail=str(exc)) from None

    for entry, spec in zip(entries, all_head_types(), strict=True):
        verdict = check_compatibility(spec, capabilities)
        entry.compatible = verdict.compatible
        entry.incompatible_reason = verdict.reason

    return HeadTypeListResponse(head_types=entries)
