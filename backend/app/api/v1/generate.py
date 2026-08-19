"""The Dataset Generator's API slice: proposals from a trained head.

Deliberately its own router rather than an addition to `annotators.py`, which describes the
*catalogue* of mask annotators. This is the tab's verbs — propose, and later save — and
keeping the noun and the verb apart is what stops one file owning both.

The response mirrors `annotate.py`'s shape on purpose. The generator reviews boxes with the
same canvas the Annotation Studio uses, and a second, subtly different payload for the same
job is how two review surfaces drift apart.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.datasets.models import Box
from app.ml import images as image_io
from app.ml.annotators.expert import HeadCannotAnnotateError, propose_boxes
from app.ml.errors import ModelNotInstalledError
from app.ml.heads.store import HeadInstanceNotFoundError, HeadInstanceStore
from app.ml.inference.engine import DEFAULT_SCORE_THRESHOLD, BackboneMismatchError

logger = logging.getLogger(__name__)
router = APIRouter()


class ExpertProposalRequest(BaseModel):
    image_path: str = Field(min_length=1)
    backbone_id: str = Field(min_length=1)
    instance_id: str = Field(min_length=1)
    score_threshold: float = Field(default=DEFAULT_SCORE_THRESHOLD, ge=0.0, le=1.0)


class ExpertProposalResponse(BaseModel):
    image_path: str
    width: int
    height: int
    device: str
    #: The user's own label for the head, and its provenance line. Both, never a
    #: filename: `summary` says what the head does ("Object detection · 2 classes")
    #: and `name` is what the user called it. Wave 3's picker shows the pair, so the
    #: generator must too or the same head reads differently in two tabs.
    head_name: str
    head_summary: str
    boxes: list[Box]


@router.post(
    "/generate/expert",
    response_model=ExpertProposalResponse,
    summary="Propose boxes for one image using a trained head",
)
async def propose_with_expert_head(
    request: ExpertProposalRequest,
) -> ExpertProposalResponse:
    try:
        image, path = image_io.read_image(request.image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    except image_io.ImageReadError as error:
        raise HTTPException(status_code=415, detail=str(error)) from None

    settings = get_settings()
    try:
        boxes = propose_boxes(
            image,
            request.backbone_id,
            request.instance_id,
            settings,
            request.score_threshold,
        )
        instance = HeadInstanceStore(settings).get(request.instance_id)
    except HeadCannotAnnotateError as exc:
        # Before the generic ValueError clause below: this is a 409, and letting it fall
        # through would report a coherent request as malformed.
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except BackboneMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ModelNotInstalledError as exc:
        raise HTTPException(
            status_code=409, detail=f"{exc} is not installed — download the backbone first."
        ) from None
    except HeadInstanceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown head: {exc}") from None
    except LookupError as exc:
        # ModelNotInstalledError subclasses LookupError, so it must be caught above or a
        # 409 silently becomes a 404.
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        # Backstop: a new raise site downstream must not escape as an opaque 500 with the
        # reason visible only in the log.
        logger.warning("Rejected expert proposal for %s: %s", request.instance_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return ExpertProposalResponse(
        image_path=str(path),
        width=image.width,
        height=image.height,
        device=settings.resolved_device,
        head_name=instance.name,
        head_summary=instance.summary,
        boxes=boxes,
    )
