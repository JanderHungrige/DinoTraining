"""Mask annotator endpoints: what can produce masks, and whether it is ready to.

Readiness is a property of a *set* of models — Grounded SAM needs two — so it is computed
here rather than left to the frontend to assemble from the model list. The admin tab should
be able to say "ready" or "needs the SAM 2.1 download" without knowing what either model is.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.paths import is_installed, resolve_model_dir
from app.ml.annotators import AnnotatorSpec, all_annotators, get_annotator
from app.ml.annotators.registry import PromptStyle
from app.ml.registry import licence_url

logger = logging.getLogger(__name__)
router = APIRouter()


class RequiredModel(BaseModel):
    id: str
    name: str
    installed: bool
    gated: bool
    approx_size_mb: int
    licence: str
    licence_url: str


class AnnotatorInfo(BaseModel):
    id: str
    name: str
    description: str
    licence: str
    licence_url: str
    gated: bool
    requires_access_request: bool
    approx_size_mb: int
    #: How this annotator wants its text: several phrases, or one concept. Carried so the
    #: UI can word its prompt hint from data rather than from an id comparison (doc 27).
    prompt_style: PromptStyle
    #: True only when every required model is installed.
    ready: bool
    #: Names of the models still to download — what to tell the user to do next.
    missing_model_ids: list[str]
    models: list[RequiredModel]


class AnnotatorListResponse(BaseModel):
    annotators: list[AnnotatorInfo]


def _describe(spec: AnnotatorSpec) -> AnnotatorInfo:
    models: list[RequiredModel] = []
    missing: list[str] = []

    for model in spec.models:
        installed = is_installed(resolve_model_dir(model.id))
        if not installed:
            missing.append(model.id)
        models.append(
            RequiredModel(
                id=model.id,
                name=model.repo_id,
                installed=installed,
                gated=model.gated,
                approx_size_mb=model.approx_size_mb,
                licence=model.licence,
                licence_url=licence_url(model),
            )
        )

    return AnnotatorInfo(
        id=spec.id,
        name=spec.name,
        description=spec.description,
        licence=spec.licence,
        licence_url=spec.licence_url,
        gated=spec.gated,
        requires_access_request=spec.requires_access_request,
        prompt_style=spec.prompt_style,
        approx_size_mb=spec.approx_size_mb,
        # Every model, not any: a half-installed Grounded SAM cannot produce a mask.
        ready=not missing,
        missing_model_ids=missing,
        models=models,
    )


@router.get(
    "/annotators",
    response_model=AnnotatorListResponse,
    summary="Mask annotators, their licences and whether they are ready to run",
)
async def list_annotators() -> AnnotatorListResponse:
    return AnnotatorListResponse(annotators=[_describe(spec) for spec in all_annotators()])


@router.get(
    "/annotators/{annotator_id}",
    response_model=AnnotatorInfo,
    summary="One mask annotator",
)
async def get_annotator_detail(annotator_id: str) -> AnnotatorInfo:
    spec = get_annotator(annotator_id)
    if spec is None:
        # The id is a key into a closed catalogue and never reaches the filesystem or the
        # network, so an unknown one is simply absent rather than a lookup to guard.
        raise HTTPException(status_code=404, detail=f"Unknown annotator: {annotator_id}")
    return _describe(spec)
