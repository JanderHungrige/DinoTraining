"""Proposing boxes with a **foundation** detector (doc 42).

Split from `generate.py` rather than added to it: that file was at 302 lines with this
included, past the project's 300-line gate. The split is along a real seam — `generate.py`
proposes from things the user *made* (a trained head) or *prompted* (a concept), and this
proposes from a model that needs neither.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.datasets.models import Box, MaskRle
from app.datasets.rle import rle_decode
from app.ml import images as image_io
from app.ml.annotators.foundation import (
    FoundationCannotAnnotateError,
    FoundationProposal,
    propose_foundation_boxes,
)
from app.ml.errors import ModelNotInstalledError
from app.ml.foundation.build import FoundationUnavailableError
from app.ml.foundation.detect import DEFAULT_SCORE_THRESHOLD as FOUNDATION_THRESHOLD
from app.ml.foundation.registry import get_foundation
from app.ml.inference.payloads import encode_png

logger = logging.getLogger(__name__)
router = APIRouter()


class FoundationProposalRequest(BaseModel):
    image_path: str = Field(min_length=1)
    foundation_id: str = Field(min_length=1)
    score_threshold: float = Field(default=FOUNDATION_THRESHOLD, ge=0.0, le=1.0)
    concept: str = Field(
        default="",
        max_length=500,
        description=(
            "Required by a concept segmenter, ignored by a detector. Grounded SAM's "
            "box half is reviewable here; its masks belong in the Inference Viewer."
        ),
    )


class ProposedMask(BaseModel):
    """The segmentation behind a box, when the model produced one (doc 61).

    Carried *beside* the box rather than instead of it: the box is the mask's extents and
    every review surface already knows how to place one, so it stays the hit target and the
    mask is what gets drawn and stored.
    """

    #: What is persisted. COCO uncompressed RLE — already the wire format.
    rle: MaskRle
    #: Preview only. Dense pixels travel as base64 PNG, never nested JSON — the Wave 3
    #: rule, measured there at 12.5 MB against 17 KB.
    png: str


class ProposedBox(BaseModel):
    """A proposed annotation: the box, and its mask when there was one."""

    box: Box
    #: None for a detector — RF-DETR has no segmentation to offer. Optional rather than
    #: absent so one shape serves both and no consumer branches on which model ran.
    mask: ProposedMask | None = None


class FoundationProposalResponse(BaseModel):
    """Deliberately the same shape as an expert proposal.

    A reviewer should not be able to tell which produced a box except by reading where it
    says it came from — so the review surface consumes one shape, not two.

    `boxes` keeps its name and its box-per-entry meaning; doc 61 added the optional mask
    *inside* each entry rather than a parallel `masks` list, because a parallel list would
    be paired by index and index pairing is what breaks the moment a reviewer removes one.
    """

    image_path: str
    width: int
    height: int
    device: str
    model_name: str
    model_summary: str
    boxes: list[ProposedBox]


@router.post(
    "/generate/foundation",
    response_model=FoundationProposalResponse,
    summary="Propose boxes for one image using a foundation detector",
)
async def propose_with_foundation(
    request: FoundationProposalRequest,
) -> FoundationProposalResponse:
    """Boxes with no prompt and nothing trained — the first useful run for a new user."""
    try:
        image, path = image_io.read_image(request.image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    except image_io.ImageReadError as error:
        raise HTTPException(status_code=415, detail=str(error)) from None

    settings = get_settings()
    try:
        proposals = propose_foundation_boxes(
            image,
            request.foundation_id,
            settings,
            request.score_threshold,
            request.concept,
        )
    except FoundationCannotAnnotateError as exc:
        # A coherent request the app is in the wrong state for — a depth model cannot be
        # reviewed as boxes. Before the ValueError backstop, or it reports as malformed.
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ModelNotInstalledError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} is not installed — download it in Admin / Models first.",
        ) from None
    except FoundationUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except LookupError as exc:
        # ModelNotInstalledError subclasses LookupError; caught above or a 409 becomes 404.
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        logger.warning("Rejected foundation proposal for %s: %s", request.foundation_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None

    spec = get_foundation(request.foundation_id)
    return FoundationProposalResponse(
        image_path=str(path),
        width=image.width,
        height=image.height,
        device=settings.resolved_device,
        model_name=spec.title if spec else request.foundation_id,
        model_summary=spec.description if spec else "",
        boxes=[_to_proposed(proposal) for proposal in proposals],
    )


def _to_proposed(proposal: FoundationProposal) -> ProposedBox:
    """Add the drawable preview to a proposal that has a mask.

    Decoding here rather than in the annotator keeps numpy out of the model layer's return
    type, the same rule `app/ml/inference/results.py` follows: what crosses that boundary is
    run lengths and floats, never an array.
    """
    if proposal.mask is None:
        return ProposedBox(box=proposal.box)
    mask = rle_decode(proposal.mask.counts, proposal.mask.size)
    return ProposedBox(
        box=proposal.box,
        # 0/255 rather than 0/1: a boolean mask rendered as a PNG would be invisible.
        mask=ProposedMask(rle=proposal.mask, png=encode_png(mask.astype("uint8") * 255)),
    )
