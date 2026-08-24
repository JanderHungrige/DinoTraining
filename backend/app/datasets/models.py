"""Domain types for annotations.

Shared by the store, the COCO exporter and the API layer, so a label or a coordinate
convention is defined exactly once.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Label = Literal["positive", "negative", "unclear"]
#: Who proposed this annotation. `expert-head` and `sam3` arrived with Wave 4;
#: `imported` with doc 31, for boxes this project did not produce at all.
#: Adding a value here is only half the change — it also lives in a SQLite CHECK
#: constraint, so it needs a migration step. See `app/datasets/migrations.py`.
Provenance = Literal[
    "grounding-dino",
    "hand-drawn",
    "expert-head",
    "sam3",
    "grounded-sam",
    "imported",
    "foundation-model",
]

LABELS: tuple[Label, ...] = ("positive", "negative", "unclear")


class Producer(BaseModel):
    """What produced an annotation, captured at write time.

    A **snapshot**, not a foreign key: a head can be deleted and its provenance must
    outlive it, because "which model made this annotation" is exactly the question asked
    of an old dataset. `provenance` says what *kind* of thing produced it; this says
    *which*.
    """

    #: Head instance id, or the annotator id. Machine-traceable.
    id: str = Field(min_length=1)
    #: Human snapshot — a head's name and summary, or the annotator's name.
    label: str = Field(min_length=1)
    #: The text concept, for annotators prompted by one.
    concept: str | None = None


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
    producer: Producer | None = None

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


class MaskRle(BaseModel):
    """One segmentation mask as uncompressed COCO run-length encoding.

    ``size`` is ``(height, width)`` — COCO's order, which is the reverse of the ``width,
    height`` used elsewhere in this module. ``counts`` alternates background/foreground run
    lengths in column-major order, always starting with background.
    """

    size: tuple[int, int]
    counts: list[int]

    @model_validator(mode="after")
    def _runs_cover_exactly_the_frame(self) -> MaskRle:
        # Imported here rather than at module scope: models.py is imported by the API layer,
        # and rle.py pulls in numpy, which the annotation types themselves do not need.
        from app.datasets.rle import validate_counts

        height, width = self.size
        if height <= 0 or width <= 0:
            raise ValueError(f"Mask size must be positive, got {width}x{height}")
        validate_counts(self.counts, height, width)
        return self


class Mask(BaseModel):
    """One reviewed segmentation mask.

    Mirrors :class:`Box` wherever the concept is the same — same three verdicts, same
    provenance vocabulary — so one review surface and one export path serve both.
    """

    label: Label
    provenance: Provenance
    rle: MaskRle
    prompt: str | None = None
    score: float | None = Field(default=None, ge=0, le=1)
    producer: Producer | None = None

    def matches_image(self, width: int, height: int) -> bool:
        return self.rle.size == (height, width)


class ImageMaskAnnotation(BaseModel):
    """Every mask for one image, as submitted by the review UI."""

    path: str = Field(min_length=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    masks: list[Mask] = Field(default_factory=list)
    prompt: str | None = None

    @model_validator(mode="after")
    def _masks_match_the_image(self) -> ImageMaskAnnotation:
        """A mask sized differently from its image is an upstream bug; storing it hides it."""
        for index, mask in enumerate(self.masks):
            if not mask.matches_image(self.width, self.height):
                mask_height, mask_width = mask.rle.size
                raise ValueError(
                    f"Mask {index} is {mask_width}x{mask_height} "
                    f"but the image is {self.width}x{self.height}"
                )
        return self


class DatasetCounts(BaseModel):
    """Live counters for the annotation UI.

    ``boxes`` and ``masks`` are separate tallies and are never summed into one "annotations"
    number: the trainer consumes them for different tasks, so a combined figure would be
    meaningless to every reader.
    """

    images: int = 0
    boxes: int = 0
    masks: int = 0
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
