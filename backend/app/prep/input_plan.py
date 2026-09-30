"""What the chosen model will do to every image, decided before training (doc 85).

A non-expert cannot know that a detector shrinks a 4000 px photo to 384 px, or that an
object 20 px across in the photo arrives as 2 px and cannot be learned. This module works
it out from the dataset's own numbers and the model's profile (doc 81), and says so:

* **the fit**: letterbox (whole picture, padded to a square), shortest edge, or a centre
  crop (classification only: the label describes the whole picture, the edges may go);
* **object sizes at the input**, the same statistics the audit judges;
* **tiling**, decided from those sizes: the smallest grid that brings the smallest tenth
  of objects up to what the model can see (`min_visible_px`). The grid is cut by
  `plan_tiles`, the one definition docs 49 and 62 already share, so what is planned here
  is what training and tiled inference will cut.

Pure functions over `DatasetFacts`. Rendering the plan onto real images is
`input_preview.py`.
"""

from __future__ import annotations

import math
from statistics import median

from pydantic import BaseModel

from app.datasets.tiling import DEFAULT_OVERLAP, grid_for, plan_tiles
from app.prep.profiles import ModelProfile
from app.prep.stats import AnnotationFacts, DatasetFacts, ImageFacts

#: Tiles along the long edge, at most. Beyond this a tile holds so little context that a
#: detector no longer learns what surrounds an object, and training time grows with n².
MAX_GRID = 6


class ObjectSizes(BaseModel):
    """Object sizes, in pixels at the model's input (the square root of the box area)."""

    median_px: float
    p10_px: float
    needed_px: int
    #: Share of objects below `needed_px`: those the model cannot learn.
    too_small_share: float


class TilingDecision(BaseModel):
    recommended: bool
    columns: int = 1
    rows: int = 1
    overlap: float = DEFAULT_OVERLAP
    #: Object sizes with this grid; None when nothing is tiled.
    objects_after: ObjectSizes | None = None
    #: False when this model's targets cannot be tiled yet (outlines, whole-image labels).
    supported: bool = True
    reason: str


class InputPlan(BaseModel):
    target: str
    label: str
    input_size: int
    #: "letterbox", "stretch", "shortest-edge" or "center-crop".
    fit: str
    fit_explained: str
    normalisation: str
    masks: str | None
    typical_source: tuple[int, int] | None
    #: Share of the model's input that is padding for the typical image.
    padding_share: float
    objects: ObjectSizes | None
    tiling: TilingDecision


def fit_of(profile: ModelProfile) -> str:
    return "center-crop" if profile.task == "classification" else profile.fit


def _scale(profile: ModelProfile, image: ImageFacts, columns: int, rows: int) -> float:
    if columns == 1 and rows == 1:
        return profile.scale_for(image.width, image.height)
    tile = plan_tiles(image.width, image.height, columns, rows)[0]
    return profile.scale_for(tile.width, tile.height)


def object_sizes(
    facts: DatasetFacts, profile: ModelProfile, long_edge_tiles: int = 1
) -> list[tuple[float, AnnotationFacts]]:
    """Every positive annotation's size at the model's input, smallest first."""
    sized: list[tuple[float, AnnotationFacts]] = []
    for annotation in facts.positives():
        image = facts.image(annotation.image_id)
        if image is None:
            continue
        columns, rows = grid_for(image.width, image.height, long_edge_tiles)
        scale = _scale(profile, image, columns, rows)
        sized.append((math.sqrt(annotation.width * annotation.height) * scale, annotation))
    sized.sort(key=lambda item: item[0])
    return sized


def summarise(sizes: list[float], needed: int) -> ObjectSizes | None:
    if not sizes:
        return None
    ordered = sorted(sizes)
    return ObjectSizes(
        median_px=round(median(ordered), 1),
        p10_px=round(ordered[len(ordered) // 10], 1),
        needed_px=needed,
        too_small_share=round(sum(1 for s in ordered if s < needed) / len(ordered), 3),
    )


def _typical(facts: DatasetFacts) -> ImageFacts | None:
    if not facts.images:
        return None
    ordered = sorted(facts.images, key=lambda i: i.width * i.height)
    return ordered[len(ordered) // 2]


def _padding(profile: ModelProfile, image: ImageFacts | None) -> float:
    if image is None or fit_of(profile) != "letterbox":
        return 0.0
    short, long = sorted((image.width, image.height))
    return round(1 - short / max(1, long), 3)


def decide_tiling(facts: DatasetFacts, profile: ModelProfile, grid: int | None) -> TilingDecision:
    """The smallest grid that lets the model see the smallest tenth of objects.

    `grid` overrides the choice (tiles along the long edge; 1 turns tiling off).
    """
    if profile.annotation_kind != "boxes":
        return TilingDecision(
            recommended=False,
            supported=False,
            reason="Tiling is available for box targets only. "
            + (
                "A whole-image label describes the whole picture, so cutting it up would "
                "give each tile a label that may not be true for it."
                if profile.annotation_kind == "labels"
                else "Outlines would have to be cut along with the picture, which is not "
                "supported yet. If objects are too small, crop the images around them "
                "before importing, or choose a model with a larger input."
            ),
        )
    needed = profile.min_visible_px
    whole = summarise([s for s, _ in object_sizes(facts, profile)], needed)
    if whole is None:
        return TilingDecision(recommended=False, reason="No annotated objects to judge.")
    chosen = grid if grid is not None else _smallest_grid(facts, profile, needed)
    if chosen <= 1:
        return TilingDecision(
            recommended=False,
            reason=f"Objects are large enough: the smallest tenth arrive at {whole.p10_px} px, "
            f"and the model needs about {needed} px."
            if whole.p10_px >= needed
            else f"Tiling is off, so {whole.too_small_share:.0%} of objects stay below the "
            f"{needed} px this model needs, and it cannot learn those.",
        )
    after = summarise([s for s, _ in object_sizes(facts, profile, chosen)], needed)
    columns, rows = _typical_grid(facts, chosen)
    enough = after is not None and after.p10_px >= needed
    return TilingDecision(
        recommended=True,
        columns=columns,
        rows=rows,
        objects_after=after,
        reason=f"Whole images shrink the smallest tenth of objects to {whole.p10_px} px, below "
        f"the {needed} px this model needs. Cut into a {columns}×{rows} grid, "
        + (
            f"they arrive at {after.p10_px if after else 0} px."
            if enough
            else f"they reach {after.p10_px if after else 0} px, still too small: this is the "
            f"largest grid worth training on. Crop closer, or choose a model with a larger input."
        ),
    )


def _smallest_grid(facts: DatasetFacts, profile: ModelProfile, needed: int) -> int:
    for tiles in range(1, MAX_GRID + 1):
        sizes = [s for s, _ in object_sizes(facts, profile, tiles)]
        if sizes and sizes[len(sizes) // 10] >= needed:
            return tiles
    return MAX_GRID


def _typical_grid(facts: DatasetFacts, tiles: int) -> tuple[int, int]:
    image = _typical(facts)
    return grid_for(image.width, image.height, tiles) if image else (tiles, tiles)


_FIT_EXPLAINED = {
    "letterbox": "The whole picture is shrunk until its long edge fits, and the rest of the "
    "square is filled with black. Nothing is cut off, and objects keep their shape.",
    "shortest-edge": "The picture is shrunk until its short edge fits, keeping its shape. "
    "Nothing is cut off.",
    "stretch": "The picture is squeezed into a square, whatever its shape. Nothing is cut "
    "off, but a wide picture's objects end up narrower than they are: a car in a 3:2 frame "
    "arrives a third slimmer. The model is used to this; it was trained the same way.",
    "center-crop": "The picture is shrunk until its short edge fits, and the centre square is "
    "kept. The edges are cut off, which is fine for a label that describes the whole "
    "picture, and wrong if what matters sits at the edge.",
}


def plan_input(facts: DatasetFacts, profile: ModelProfile, grid: int | None = None) -> InputPlan:
    typical = _typical(facts)
    fit = fit_of(profile)
    sizes = [s for s, _ in object_sizes(facts, profile)]
    return InputPlan(
        target=profile.id,
        label=profile.label,
        input_size=profile.input_size,
        fit=fit,
        fit_explained=_FIT_EXPLAINED[fit],
        normalisation="Colours are rescaled with the statistics the model was trained on. "
        "This happens automatically; there is nothing to set.",
        masks=(
            "Outlines are resized with the picture, pixel for pixel (no blending, which would "
            "invent classes), and the black padding is marked 'ignore', so the model is not "
            "taught that padding is background."
            if profile.annotation_kind == "masks"
            else None
        ),
        typical_source=(typical.width, typical.height) if typical else None,
        padding_share=_padding(profile, typical),
        objects=summarise(sizes, profile.min_visible_px)
        if profile.task != "classification"
        else None,
        tiling=decide_tiling(facts, profile, grid),
    )


__all__ = [
    "MAX_GRID",
    "InputPlan",
    "ObjectSizes",
    "TilingDecision",
    "decide_tiling",
    "fit_of",
    "grid_for",
    "object_sizes",
    "plan_input",
    "summarise",
]
