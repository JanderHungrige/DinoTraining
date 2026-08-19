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
from app.datasets.models import Box, Label, MaskRle, Provenance
from app.datasets.rle import rle_decode
from app.ml import images as image_io
from app.ml.annotators.base import MaskProposal
from app.ml.annotators.build import AnnotatorUnavailableError, build_annotator
from app.ml.annotators.expert import HeadCannotAnnotateError, propose_boxes
from app.ml.annotators.grounded_sam import PROVENANCE
from app.ml.annotators.registry import GROUNDED_SAM, get_annotator
from app.ml.detector import DEFAULT_BOX_THRESHOLD
from app.ml.errors import ModelNotInstalledError
from app.ml.heads.store import HeadInstanceNotFoundError, HeadInstanceStore
from app.ml.inference.engine import DEFAULT_SCORE_THRESHOLD, BackboneMismatchError
from app.ml.inference.payloads import encode_png

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


class MaskProposalRequest(BaseModel):
    image_path: str = Field(min_length=1)
    concept: str = Field(min_length=1, max_length=500)
    annotator_id: str = Field(default=GROUNDED_SAM)
    threshold: float = Field(default=DEFAULT_BOX_THRESHOLD, ge=0.0, le=1.0)


class ProposedMask(BaseModel):
    """One proposal: the RLE that gets stored, plus a preview that gets drawn."""

    label: Label = "positive"
    provenance: Provenance
    #: What is persisted. COCO uncompressed RLE — already the wire format.
    rle: MaskRle
    #: Derived on the server so no client decodes an RLE to place an overlay.
    x: float
    y: float
    w: float
    h: float
    score: float
    concept: str
    #: Preview only. Dense pixels travel as base64 PNG, never nested JSON — the Wave 3
    #: rule, measured there at 12.5 MB against 17 KB.
    mask_png: str


class MaskProposalResponse(BaseModel):
    image_path: str
    width: int
    height: int
    device: str
    annotator_id: str
    annotator_name: str
    masks: list[ProposedMask]


@router.post(
    "/generate/masks",
    response_model=MaskProposalResponse,
    summary="Propose segmentation masks for one image from a text concept",
)
async def propose_masks(request: MaskProposalRequest) -> MaskProposalResponse:
    spec = get_annotator(request.annotator_id)
    if spec is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown annotator: {request.annotator_id}"
        )

    try:
        image, path = image_io.read_image(request.image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    except image_io.ImageReadError as error:
        raise HTTPException(status_code=415, detail=str(error)) from None

    settings = get_settings()
    try:
        annotator = build_annotator(request.annotator_id)
        proposals = annotator.propose(image, request.concept, threshold=request.threshold)
    except AnnotatorUnavailableError as exc:
        # Catalogued but not yet built. 501 rather than 404: the id is real and the user
        # did nothing wrong, so "not found" would send them looking for a typo.
        raise HTTPException(status_code=501, detail=str(exc)) from None
    except ModelNotInstalledError as exc:
        # Before LookupError, or "download this first" becomes an opaque 404.
        raise HTTPException(
            status_code=409,
            detail=(
                f"{exc} is not installed. Download it from the Admin tab — "
                f"{spec.name} needs {', '.join(spec.model_ids)}."
            ),
        ) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        logger.warning("Rejected mask proposal for %s: %s", request.annotator_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return MaskProposalResponse(
        image_path=str(path),
        width=image.width,
        height=image.height,
        device=settings.resolved_device,
        annotator_id=spec.id,
        annotator_name=spec.name,
        masks=[_to_proposed_mask(proposal) for proposal in proposals],
    )


def _to_proposed_mask(proposal: MaskProposal) -> ProposedMask:
    mask = rle_decode(proposal.counts, proposal.size)
    return ProposedMask(
        provenance=PROVENANCE,
        rle=MaskRle(size=proposal.size, counts=proposal.counts),
        x=proposal.box[0],
        y=proposal.box[1],
        w=proposal.box[2],
        h=proposal.box[3],
        score=proposal.score,
        concept=proposal.concept,
        # 0/255 rather than 0/1: a boolean mask rendered as a PNG would be invisible.
        mask_png=encode_png((mask.astype("uint8")) * 255),
    )
