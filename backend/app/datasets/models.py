"""Domain types for annotations.

Shared by the store, the COCO exporter and the API layer, so a label or a coordinate
convention is defined exactly once.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Label = Literal["positive", "negative", "unclear"]
Provenance = Literal["grounding-dino", "hand-drawn"]

LABELS: tuple[Label, ...] = ("positive", "negative", "unclear")


class Box(BaseModel):
    """One bounding box.

    Absolute pixels, origin top-left, ``x``/``y`` at the top-left corner — the same
    convention COCO uses, so exporting is a copy rather than a conversion.
    """

    label: Label
    provenance: Provenance
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    w: float = Field(gt=0, description="Width in pixels; a zero-area box is not a box.")
    h: float = Field(gt=0)
    prompt: str | None = None
    score: float | None = Field(default=None, ge=0, le=1)

    def fits_within(self, width: int, height: int) -> bool:
        return self.x + self.w <= width and self.y + self.h <= height


class ImageAnnotation(BaseModel):
    """Every box for one image, as submitted by the annotation UI."""

    path: str = Field(min_length=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    boxes: list[Box] = Field(default_factory=list)
    prompt: str | None = None

    @model_validator(mode="after")
    def _boxes_fit_the_image(self) -> ImageAnnotation:
        """A box outside the frame is a bug upstream; storing it hides that bug."""
        for index, box in enumerate(self.boxes):
            if not box.fits_within(self.width, self.height):
                raise ValueError(
                    f"Box {index} ({box.x},{box.y},{box.w},{box.h}) "
                    f"extends outside the {self.width}x{self.height} image"
                )
        return self


class DatasetCounts(BaseModel):
    """Live counters for the annotation UI."""

    images: int = 0
    boxes: int = 0
    positive: int = 0
    negative: int = 0
    unclear: int = 0


class DatasetInfo(BaseModel):
    id: str
    name: str
    created_at: str
    prompt: str | None
    copy_images: bool
    counts: DatasetCounts
