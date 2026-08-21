"""Foundation-model endpoints: what is offered, and running one over an image.

Kept apart from `/inference` because the thing being run is different in kind, not just in
configuration. `/inference` composes a backbone pass with N heads; a foundation model *is*
the whole prediction. Both return the same `PredictionResponse`, which is what lets the
viewer and the overlay registry treat them alike.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel, Field

from app.api.v1.inference import PredictionResponse, describe
from app.core.paths import is_installed, resolve_model_dir
from app.ml.annotators.registry import get_annotator
from app.ml.errors import ModelNotInstalledError
from app.ml.foundation.build import (
    FoundationImplementation,
    FoundationUnavailableError,
    build_foundation,
)
from app.ml.foundation.concept import ConceptSegmenter
from app.ml.foundation.detect import DEFAULT_SCORE_THRESHOLD, RfDetrModel
from app.ml.foundation.instances import FoundationInstance, FoundationInstanceStore
from app.ml.foundation.registry import FoundationSpec, all_foundations, get_foundation
from app.ml.images import ImageReadError, read_image
from app.ml.inference.results import Prediction
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
    #: True when this model needs a text concept before it predicts anything (doc 45).
    #: The picker shows a concept field for these and hides it for everything else.
    takes_concept: bool = False


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
    concept: str = Field(
        default="",
        max_length=500,
        description=(
            "What to segment, for a concept-prompted model. Ignored by the others — an "
            "RF-DETR predicts its 91 COCO classes whatever you type at it."
        ),
    )


def _run(
    model: FoundationImplementation, image: Image.Image, request: FoundationRunRequest
) -> Prediction:
    """The one place that asks *what kind* of model this is.

    Not an id→implementation map — `build_foundation` remains the only one of those — but a
    capability check: a detector takes a score threshold, a concept segmenter takes a
    concept as well, and a depth map has nothing to threshold. A uniform signature would
    mean two of the three accepting an argument they ignore.
    """
    if isinstance(model, ConceptSegmenter):
        return model.predict(image, request.concept, request.score_threshold)
    if isinstance(model, RfDetrModel):
        return model.predict(image, request.score_threshold)
    return model.predict(image)


def _describe(spec_id: str) -> FoundationInfo:
    spec = get_foundation(spec_id)
    if spec is None:  # pragma: no cover - callers iterate the registry
        raise FoundationUnavailableError(spec_id)
    if spec.annotator_id is not None:
        return _describe_pipeline(spec, spec.annotator_id)
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
        takes_concept=spec.takes_concept,
    )


def _describe_pipeline(spec: FoundationSpec, annotator_id: str) -> FoundationInfo:
    """A concept segmenter chains several checkpoints, so `model_id` answers neither
    "is it installed?" nor "what does it cost?" — **every** model in the chain must be
    present, and the download is their sum. The strictest licence in the chain governs,
    for the same reason a chain is only as permissive as its least permissive link."""
    annotator = get_annotator(annotator_id)
    if annotator is None:  # pragma: no cover - packaging error, not user input
        raise RuntimeError(f"{spec.id} names unknown annotator {annotator_id}")
    models = annotator.models
    return FoundationInfo(
        id=spec.id,
        title=spec.title,
        description=spec.description,
        task=spec.task,
        render_hint=spec.render_hint,
        model_id=spec.model_id,
        licence=annotator.licence,
        non_commercial=any(model.non_commercial for model in models),
        installed=all(is_installed(resolve_model_dir(m.id)) for m in models),
        approx_size_mb=annotator.approx_size_mb,
        takes_concept=True,
    )



@router.get(
    "/foundation",
    response_model=FoundationListResponse,
    summary="Self-contained models that predict without a head",
)
async def list_foundations() -> FoundationListResponse:
    """Catalogue entries **and** the models the user fine-tuned, in one list.

    One list on purpose: a fine-tuned detector is picked, run and reviewed exactly like a
    downloaded one, and splitting them would make every consumer learn a distinction that
    changes nothing about how it is used.
    """
    entries = [_describe(spec.id) for spec in all_foundations()]
    for instance in FoundationInstanceStore().list_all():
        entries.append(_describe_instance(instance))
    return FoundationListResponse(foundations=entries)


def _describe_instance(instance: FoundationInstance) -> FoundationInfo:
    base = get_model(instance.base_model_id)
    return FoundationInfo(
        id=instance.id,
        title=instance.name,
        description=instance.summary,
        task="detection",
        render_hint="boxes",
        model_id=instance.base_model_id,
        # A fine-tune inherits its base model's licence: it *is* that model's weights,
        # moved. Training on your own data does not relicense someone else's checkpoint.
        licence=base.licence if base else "unknown",
        non_commercial=bool(base and base.non_commercial),
        # Always: the weights are on this machine because this machine made them.
        installed=True,
        approx_size_mb=0,
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
        prediction = _run(model, image, request)
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
