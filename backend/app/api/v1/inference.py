"""Run one head over one image on disk.

**Path-based, not multipart.** Wave 1 established that this is a desktop app whose
images live in a folder the user picked (`app/ml/images.py`), so the client sends a path
and the backend reads it. Adding an upload endpoint would mean a second input contract
and would push megabytes over loopback for a file already on the same machine.

The threat model is Wave 1's and unchanged: confinement is not the control, because the
user genuinely does point this at arbitrary folders. Instead every read is narrowed to
"a file PIL opens as one of a small set of image formats", which turns "read any file"
into "confirm a file is a valid image".

Status codes: 404 unknown head or missing file, 409 wrong or uninstalled backbone,
415 not a readable image, 422 well-formed request whose values do not fit.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException, Query
from PIL.Image import Image as ImageType
from pydantic import BaseModel, Field

from app.ml.errors import ModelNotInstalledError
from app.ml.heads.registry import RenderHint
from app.ml.heads.store import HeadInstanceNotFoundError
from app.ml.images import ImageReadError, read_image
from app.ml.inference.compose import run_heads
from app.ml.inference.engine import (
    DEFAULT_SCORE_THRESHOLD,
    BackboneMismatchError,
    run_inference,
)
from app.ml.inference.results import Prediction
from app.ml.inference.source import InputSource, SourceKind, resolve_source

logger = logging.getLogger(__name__)
router = APIRouter()


class InferenceRequest(BaseModel):
    image_path: str = Field(description="Absolute path to an image on this machine.")
    backbone_id: str = Field(description="Registry id of an installed backbone.")
    instance_id: str = Field(description="Head instance id from GET /heads.")
    score_threshold: float = Field(
        default=DEFAULT_SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Detection only; ignored by other render hints.",
    )


class PredictionResponse(BaseModel):
    instance_id: str
    head_name: str = Field(description="Provenance-bearing name, never a filename.")
    head_type_id: str
    task: str
    render_hint: RenderHint = Field(description="What the overlay renderer dispatches on.")
    class_names: list[str]
    payload: dict[str, object] = Field(description="Shape depends on render_hint.")
    grid: list[int]
    elapsed_ms: float


def describe(prediction: Prediction) -> PredictionResponse:
    return PredictionResponse(
        instance_id=prediction.instance_id,
        head_name=prediction.head_name,
        head_type_id=prediction.head_type_id,
        task=prediction.task,
        render_hint=prediction.render_hint,
        class_names=list(prediction.class_names),
        payload=prediction.payload,
        grid=list(prediction.grid),
        elapsed_ms=prediction.elapsed_ms,
    )


class ComposeRequest(BaseModel):
    image_path: str = Field(description="Absolute path to an image on this machine.")
    backbone_id: str = Field(description="Registry id of an installed backbone.")
    instance_ids: list[str] = Field(
        min_length=1,
        description="Head instance ids from GET /heads. Duplicates are collapsed.",
    )
    score_threshold: float = Field(
        default=DEFAULT_SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Detection only; ignored by other render hints.",
    )


class ComposedResponse(BaseModel):
    predictions: list[PredictionResponse] = Field(
        description="One per head, in the order they were requested."
    )
    passes: int = Field(description="Backbone forward passes actually run.")
    elapsed_ms: float = Field(
        description="Wall clock for everything. Per-head timings sum to less — the "
        "difference is the shared backbone pass."
    )


class SourceItemResponse(BaseModel):
    item_id: str = Field(description="Stable, opaque identity — never a path.")
    name: str
    path: str = Field(description="Absolute path, for image bytes and POST /inference.")


class SourceResponse(BaseModel):
    kind: SourceKind
    root: str
    items: list[SourceItemResponse]
    truncated: bool = Field(description="True when the folder held more than the cap.")


def describe_source(source: InputSource) -> SourceResponse:
    return SourceResponse(
        kind=source.kind,
        root=str(source.root),
        items=[
            SourceItemResponse(item_id=item.item_id, name=item.name, path=str(item.path))
            for item in source.items
        ],
        truncated=source.truncated,
    )


@router.get(
    "/inference/source",
    response_model=SourceResponse,
    summary="Resolve a path into the images to step through",
)
async def read_source(path: str = Query(min_length=1)) -> SourceResponse:
    """A single image or a folder, returned as one shape.

    An empty folder is a 200 with no items, not a 404: "this folder has no images in it"
    is a routine thing for a user to discover and the viewer has to be able to say it.
    """
    try:
        source = resolve_source(path)
    # ImageReadError subclasses ValueError; FolderNotFoundError subclasses FileNotFoundError.
    except ImageReadError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from None
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None

    return describe_source(source)


def load_or_reject(image_path: str) -> ImageType:
    """Read the image, or map the failure onto the documented status codes."""
    try:
        image, _ = read_image(image_path)
    except ImageReadError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from None
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return image


@contextmanager
def translated_errors(label: str) -> Iterator[None]:
    """Map head-running failures onto status codes, in the one order that is correct.

    Shared by both routes so the ordering discipline lives in a single place: several
    project errors subclass ``LookupError`` or ``ValueError``, and catching the general
    one first silently turns a 409 into a 404.
    """
    try:
        yield
    except HeadInstanceNotFoundError as exc:
        # The exception carries the offending id. Reporting the whole request's list
        # instead would leave the user guessing which of their heads to fix.
        raise HTTPException(status_code=404, detail=f"Unknown head: {exc}") from None
    # ModelNotInstalledError subclasses LookupError, so it must precede the bare catch.
    except ModelNotInstalledError as exc:
        raise HTTPException(
            status_code=409, detail=f"{exc} is not installed — download the backbone first."
        ) from None
    except BackboneMismatchError as exc:
        # 409 rather than 422: the request is coherent, the app is simply in the wrong
        # state for it, and the message names the backbone that would work.
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        # Backstop, as in the head-catalogue router: everything downstream signals bad
        # input with ValueError, and one escaping reaches the user as an opaque 500
        # with the reason only in the log.
        logger.error("Inference rejected for %s: %s", label, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post(
    "/inference",
    response_model=PredictionResponse,
    summary="Run one head instance over one image",
)
async def infer(request: InferenceRequest) -> PredictionResponse:
    image = load_or_reject(request.image_path)

    with translated_errors(request.instance_id):
        prediction = run_inference(
            image,
            backbone_id=request.backbone_id,
            instance_id=request.instance_id,
            score_threshold=request.score_threshold,
        )

    return describe(prediction)


@router.post(
    "/inference/compose",
    response_model=ComposedResponse,
    summary="Run several head instances over one image, sharing backbone passes",
)
async def compose(request: ComposeRequest) -> ComposedResponse:
    """N heads, one pass per framing.

    A mismatched or unknown head fails the whole request rather than being skipped:
    partial success would be a second response shape for every consumer to handle, and
    the viewer only offers heads registered for the selected backbone.
    """
    image = load_or_reject(request.image_path)

    with translated_errors(", ".join(request.instance_ids) or "(no heads)"):
        result = run_heads(
            image,
            backbone_id=request.backbone_id,
            instance_ids=list(request.instance_ids),
            score_threshold=request.score_threshold,
        )

    return ComposedResponse(
        predictions=[describe(prediction) for prediction in result.predictions],
        passes=result.passes,
        elapsed_ms=result.elapsed_ms,
    )
