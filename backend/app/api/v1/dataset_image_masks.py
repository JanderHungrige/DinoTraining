"""One image's stored masks, for reopening it in the Studio (doc 61).

Its own module for the reason `dataset_classes.py` is: `datasets.py` is at 291 lines
against the project's 300-line gate.

**Why this is not part of the dataset listing.** `GET /datasets/{id}/images` ships every
image's boxes inline, which is right — a box is four floats, and fetching them per image
would put a round trip behind every press of Next. A mask is not four floats. Its RLE is a
run list over the whole frame, roughly 15 KB as JSON for a 2464x1600 mask, and the OSDaR23
rail dataset is 392 images. Inline masks would make that listing enormous to answer a
question about one image. The Studio shows one image at a time, so it asks for one.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.datasets.masks import MaskStore
from app.datasets.models import Mask
from app.datasets.rle import rle_bbox, rle_decode
from app.datasets.store import DatasetStore
from app.ml.inference.payloads import encode_png

logger = logging.getLogger(__name__)
router = APIRouter()


class StoredMask(BaseModel):
    """One stored mask, with the preview the canvas draws.

    `x/y/w/h` is the mask's own bounding box, derived on write by `MaskStore._row` — so
    nothing here decodes an RLE to place an overlay, and the review surface gets the same
    hit target a box gives it.
    """

    label: str
    provenance: str
    rle: dict[str, object]
    x: float
    y: float
    w: float
    h: float
    score: float | None = None
    prompt: str | None = None
    producer: dict[str, object] | None = None
    #: Preview only. Dense pixels travel as base64 PNG, never nested JSON.
    mask_png: str


class ImageMasksResponse(BaseModel):
    path: str
    masks: list[StoredMask]


@router.get(
    "/datasets/{dataset_id}/images/masks",
    response_model=ImageMasksResponse,
    summary="One image's stored segmentation masks",
)
async def get_image_masks(
    dataset_id: str,
    path: str = Query(min_length=1, description="Stored path, as the listing reports it."),
) -> ImageMasksResponse:
    """The masks one image carries. Empty for an image that has none.

    An unknown dataset is a 404; an unknown *path* is an empty list. To a review surface
    opening on an image those are different questions — the first means the caller is
    pointed at nothing, the second means this picture has not been segmented yet, which is
    the ordinary case and must not read as a failure.
    """
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_id}")

    masks = MaskStore().masks_for_image(dataset_id, path)
    logger.debug("%d mask(s) for %s in %s", len(masks), path, dataset_id)
    return ImageMasksResponse(path=path, masks=[_to_stored(mask) for mask in masks])


def _to_stored(mask: Mask) -> StoredMask:
    """Add the drawable preview and the derived box.

    The bbox is re-derived through `rle_bbox` rather than read back from the row because
    `masks_for_image` returns the domain `Mask`, which is the *stored annotation* and
    deliberately carries no bbox — the columns exist so a listing never has to decode an
    RLE, and this route decodes anyway to build the PNG. Same helper the write path uses,
    so the box a reviewer clicks is the box the export reports, to the pixel.
    """
    decoded = rle_decode(mask.rle.counts, mask.rle.size)
    # An all-background mask cannot be stored — `MaskStore._row` rejects it — so anything
    # out of the database has a box. The fallback is for a database edited by hand.
    x, y, w, h = rle_bbox(mask.rle.counts, mask.rle.size) or (0.0, 0.0, 1.0, 1.0)
    return StoredMask(
        label=mask.label,
        provenance=mask.provenance,
        rle={"size": list(mask.rle.size), "counts": mask.rle.counts},
        x=float(x),
        y=float(y),
        w=float(w),
        h=float(h),
        score=mask.score,
        prompt=mask.prompt,
        producer=mask.producer.model_dump() if mask.producer else None,
        # 0/255 rather than 0/1: a boolean mask rendered as a PNG would be invisible.
        mask_png=encode_png(decoded.astype("uint8") * 255),
    )
