"""Foundation-model endpoints: what is offered, and running one over an image.

Kept apart from `/inference` because the thing being run is different in kind, not just in
configuration. `/inference` composes a backbone pass with N heads; a foundation model *is*
the whole prediction. Both return the same `PredictionResponse`, which is what lets the
viewer and the overlay registry treat them alike.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.inference import PredictionResponse, describe
from app.core.paths import is_installed, resolve_model_dir
from app.ml.errors import ModelNotInstalledError
from app.ml.foundation.build import FoundationUnavailableError, build_foundation
from app.ml.foundation.detect import DEFAULT_SCORE_THRESHOLD, RfDetrModel
from app.ml.foundation.registry import all_foundations, get_foundation
from app.ml.images import ImageReadError, read_image
from app.ml.registry import get_model

logger = logging.getLogger(__name__)
router = APIRouter()


class FoundationInfo(BaseModel):
    """One foundation model as the picker shows it."""

    id: str
    title: str
    description: str
    task: str
    render_hint: str
    model_id: str
    licence: str
    #: Surfaced here too, not only in the admin panel: the viewer is where a user meets a
    #: model they have already installed, and "may I use this output?" is asked there.
    non_commercial: bool
    installed: bool
    approx_size_mb: int


class FoundationListResponse(BaseModel):
    foundations: list[FoundationInfo]


class FoundationRunRequest(BaseModel):
    image_path: str = Field(min_length=1)
    foundation_id: str = Field(min_length=1)
    score_threshold: float = Field(
        default=DEFAULT_SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Detection only; a depth model has nothing to threshold.",
    )


def _describe(spec_id: str) -> FoundationInfo:
    spec = get_foundation(spec_id)
    if spec is None:  # pragma: no cover - callers iterate the registry
        raise FoundationUnavailableError(spec_id)
    model = get_model(spec.model_id)
    if model is None:
        # A foundation spec naming a model the catalogue does not have is a packaging
        # error, not user input. Loud rather than silently unlisted.
        raise RuntimeError(f"{spec.id} names unknown model {spec.model_id}")
    return FoundationInfo(
        id=spec.id,
        title=spec.title,
        description=spec.description,
        task=spec.task,
        render_hint=spec.render_hint,
        model_id=spec.model_id,
        licence=model.licence,
        non_commercial=model.non_commercial,
        installed=is_installed(resolve_model_dir(spec.model_id)),
        approx_size_mb=model.approx_size_mb,
    )


@router.get(
    "/foundation",
    response_model=FoundationListResponse,
    summary="Self-contained models that predict without a head",
)
async def list_foundations() -> FoundationListResponse:
    return FoundationListResponse(
        foundations=[_describe(spec.id) for spec in all_foundations()]
    )


@router.post(
    "/foundation/predict",
    response_model=PredictionResponse,
    summary="Run one foundation model over one image",
)
async def predict(request: FoundationRunRequest) -> PredictionResponse:
    """Run a foundation model and return the same shape a head would.

    Error ordering matters and is the same discipline as `/inference`:
    `ModelNotInstalledError` subclasses `LookupError`, so it is caught first or a 409
    ("download it") silently becomes a 404 ("no such thing").

    Image failures use the codes the rest of the API already uses — 404 for absent, 415
    for unreadable — rather than a third convention for the same two problems. The first
    version of this handler had neither, and a missing file reached the user as a 500:
    `FileNotFoundError` is an `OSError`, so it slipped past both the `LookupError` and the
    `ValueError` backstop that were supposed to make that impossible.
    """
    try:
        image, _ = read_image(request.image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    except ImageReadError as exc:
        # Subclasses ValueError, so it must precede the backstop below.
        raise HTTPException(status_code=415, detail=str(exc)) from None

    try:
        model = build_foundation(request.foundation_id)
        # The one place that asks *what kind* of model this is. Not an id→implementation
        # map — `build_foundation` remains the only one of those — but a capability check:
        # a detector takes a score threshold and a depth map has nothing to threshold, so
        # a uniform signature would mean one of them accepting an argument it ignores.
        prediction = (
            model.predict(image, request.score_threshold)
            if isinstance(model, RfDetrModel)
            else model.predict(image)
        )
    except ModelNotInstalledError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} is not installed — download it in Admin / Models first.",
        ) from None
    except FoundationUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        # Backstop: a new raise site downstream must not reach the user as a 500 with the
        # reason only in the log.
        logger.error("Foundation run rejected for %s: %s", request.foundation_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return describe(prediction)
