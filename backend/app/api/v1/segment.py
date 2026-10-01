"""Editing an outline (doc 106): SAM 2 clicks, outlines from boxes, brush and eraser."""

from __future__ import annotations

import asyncio
import logging

import numpy as np
import numpy.typing as npt
from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel, Field

from app.datasets.rle import rle_bbox, rle_decode, rle_encode
from app.ml import images as image_io
from app.ml.errors import ModelNotInstalledError
from app.ml.inference.payloads import encode_png
from app.ml.mask_strokes import apply_stroke
from app.ml.segmenter import (
    DEFAULT_SEGMENTER,
    Segmenter,
    load_segmenter,
    segment_boxes,
    segment_refined,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class Rect(BaseModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    w: float = Field(gt=0)
    h: float = Field(gt=0)


class ClickPoint(BaseModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    #: True: include this spot (⊕); False: exclude it (⊖).
    positive: bool


class RefineRequest(BaseModel):
    image_path: str = Field(min_length=1)
    box: Rect
    points: list[ClickPoint] = Field(default_factory=list, max_length=50)
    model_id: str = DEFAULT_SEGMENTER


class BoxesRequest(BaseModel):
    image_path: str = Field(min_length=1)
    boxes: list[Rect] = Field(min_length=1, max_length=200)
    model_id: str = DEFAULT_SEGMENTER


class RleIn(BaseModel):
    size: tuple[int, int]
    counts: list[int]


class StrokeRequest(BaseModel):
    rle: RleIn
    points: list[tuple[float, float]] = Field(min_length=1, max_length=5000)
    radius: float = Field(gt=0, le=500)
    erase: bool = False


class EditedMask(BaseModel):
    rle: dict[str, object]
    mask_png: str
    x: float
    y: float
    w: float
    h: float
    score: float | None = None


class EditedMasks(BaseModel):
    masks: list[EditedMask]


def _edited(mask: npt.NDArray[np.bool_], score: float | None) -> EditedMask:
    counts, size = rle_encode(mask)
    bbox = rle_bbox(counts, size)
    if bbox is None:
        raise ValueError("Nothing would be left of this outline — reject it instead.")
    x, y, w, h = bbox
    return EditedMask(
        rle={"size": list(size), "counts": counts},
        mask_png=encode_png(mask.astype("uint8") * 255),
        x=float(x),
        y=float(y),
        w=float(w),
        h=float(h),
        score=score,
    )


def _open(image_path: str, model_id: str) -> tuple[Image.Image, Segmenter]:
    try:
        image, _ = image_io.read_image(image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    except image_io.ImageReadError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    try:
        return image, load_segmenter(model_id)
    except ModelNotInstalledError:
        raise HTTPException(
            status_code=404,
            detail=f"{model_id} is not installed. Download it in Models & Datasets first.",
        ) from None
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}") from None


def _inside(rect: Rect, width: int, height: int) -> None:
    if rect.x >= width or rect.y >= height:
        raise ValueError("The box lies outside the picture.")


@router.post(
    "/segment/refine", response_model=EditedMask, summary="One outline from a box and clicks"
)
async def refine(request: RefineRequest) -> EditedMask:
    image, segmenter = _open(request.image_path, request.model_id)
    try:
        _inside(request.box, image.width, image.height)
        if any(p.x >= image.width or p.y >= image.height for p in request.points):
            raise ValueError("A point lies outside the picture.")
        box = request.box
        mask, score = await asyncio.to_thread(
            segment_refined,
            segmenter,
            image,
            (box.x, box.y, box.x + box.w, box.y + box.h),
            [(p.x, p.y, p.positive) for p in request.points],
        )
        return _edited(mask, score)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/segment/boxes", response_model=EditedMasks, summary="An outline for each box (SAM 2)"
)
async def outlines_from_boxes(request: BoxesRequest) -> EditedMasks:
    image, segmenter = _open(request.image_path, request.model_id)
    try:
        for rect in request.boxes:
            _inside(rect, image.width, image.height)
        prompts = [(b.x, b.y, b.x + b.w, b.y + b.h) for b in request.boxes]
        masks, scores = await asyncio.to_thread(segment_boxes, segmenter, image, prompts)
        logger.info("Outlined %d box(es) in %s", len(prompts), request.image_path)
        return EditedMasks(masks=[_edited(m, s) for m, s in zip(masks, scores, strict=True)])
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/segment/stroke", response_model=EditedMask, summary="Paint or erase along a stroke")
async def stroke(request: StrokeRequest) -> EditedMask:
    try:
        mask = rle_decode(request.rle.counts, request.rle.size)
        painted = apply_stroke(mask, list(request.points), request.radius, request.erase)
        return _edited(painted, None)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


__all__ = ["router"]
