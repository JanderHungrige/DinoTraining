"""Prompted box proposals, folder listing, and image streaming for the canvas."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.datasets.models import Box
from app.ml import images as image_io
from app.ml.detector import (
    DEFAULT_BOX_THRESHOLD,
    DEFAULT_DETECTOR,
    DEFAULT_TEXT_THRESHOLD,
    ModelNotInstalledError,
    detect,
    load_detector,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class AnnotateRequest(BaseModel):
    image_path: str = Field(min_length=1)
    prompt: str = Field(min_length=1, max_length=500)
    box_threshold: float = Field(default=DEFAULT_BOX_THRESHOLD, ge=0.0, le=1.0)
    text_threshold: float = Field(default=DEFAULT_TEXT_THRESHOLD, ge=0.0, le=1.0)
    model_id: str = Field(default=DEFAULT_DETECTOR)


class ProposedBox(Box):
    """A stored box plus the phrase that produced it."""

    text: str = ""


class AnnotateResponse(BaseModel):
    image_path: str
    width: int
    height: int
    prompt: str
    device: str
    boxes: list[ProposedBox]


class FolderListing(BaseModel):
    folder: str
    images: list[str]


@router.post("/annotate", response_model=AnnotateResponse, summary="Propose boxes for an image")
async def annotate(request: AnnotateRequest) -> AnnotateResponse:
    try:
        image, path = image_io.read_image(request.image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    except image_io.ImageReadError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None

    try:
        detector = load_detector(request.model_id)
    except ModelNotInstalledError:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{request.model_id} is not installed. "
                "Download it in the Admin tab before annotating."
            ),
        ) from None
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Unknown model: {request.model_id}") from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None

    # Forward passes are CPU/GPU-bound and can take seconds; off the event loop they
    # go, or the health probe stalls behind them.
    detections = await asyncio.to_thread(
        detect, detector, image, request.prompt, request.box_threshold, request.text_threshold
    )

    logger.info("Proposed %d boxes for %s", len(detections), path.name)
    return AnnotateResponse(
        image_path=str(path),
        width=image.width,
        height=image.height,
        prompt=request.prompt,
        device=detector.device,
        boxes=[
            # Proposals arrive as `positive`: that is what the detector is asserting,
            # and the user's job is to downgrade the wrong ones.
            ProposedBox(
                label="positive",
                provenance="grounding-dino",
                x=d.x,
                y=d.y,
                w=d.w,
                h=d.h,
                score=min(d.score, 1.0),
                prompt=request.prompt,
                text=d.text,
            )
            for d in detections
        ],
    )


@router.get("/annotate/folder", response_model=FolderListing, summary="List images in a folder")
async def list_folder(path: str = Query(min_length=1)) -> FolderListing:
    try:
        found = image_io.list_images(path)
    except image_io.FolderNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None

    return FolderListing(folder=path, images=[str(entry) for entry in found])


@router.get("/annotate/image", summary="Stream a local image for the canvas")
async def get_image(path: str = Query(min_length=1)) -> FileResponse:
    """The webview cannot load file:// URLs, so the backend serves the bytes."""
    try:
        _, resolved = image_io.read_image(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    except image_io.ImageReadError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None

    return FileResponse(resolved)
