""" "What the model sees": sampled images put through the real plan (doc 85).

The most important picture in data preparation. A number like "objects arrive at 1.7 px"
means little to someone who has never trained a model; a 384 px picture in which the
signal is two grey pixels means everything.

**The real functions, not a drawing of them.** Images go through `apply_geometry` and
boxes through `transform_boxes`, masks through `transform_mask`: exactly what training
does (doc 10). A preview that re-derived the geometry could agree with itself and not with
training, which is the one thing it exists to rule out.

The picture is returned at the model's own resolution. The UI enlarges it without
smoothing, so the user sees the pixels the model gets.
"""

from __future__ import annotations

import base64
import colorsys
import io
import logging
import random
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw
from pydantic import BaseModel

from app.datasets.class_names import normalise_class_name
from app.datasets.masks import MaskStore
from app.datasets.rle import rle_decode
from app.datasets.tiling import Tile, plan_tiles
from app.ml.preprocess import (
    IMAGENET_MEAN,
    IMAGENET_STD,
    Box,
    GeometryTransform,
    PreprocessPlan,
    apply_geometry,
    transform_boxes,
    transform_mask,
)
from app.prep.input_plan import InputPlan, fit_of, grid_for, object_sizes
from app.prep.profiles import ModelProfile
from app.prep.stats import AnnotationFacts, DatasetFacts, ImageFacts

logger = logging.getLogger(__name__)

MAX_PREVIEWS = 12
_PALETTE = ("#38bdf8", "#a3e635", "#fbbf24", "#f472b6", "#a78bfa", "#2dd4bf", "#fb923c")
#: Objects the model cannot see are drawn in this, whatever their class.
TOO_SMALL_COLOUR = "#ef4444"


class PreviewImage(BaseModel):
    path: str
    #: The tile shown, [x, y, width, height] in the source image; None for the whole image.
    tile: tuple[int, int, int, int] | None
    #: A JPEG data URL, at the model's input resolution.
    data_url: str
    width: int
    height: int
    objects: int
    #: Objects cut away entirely by the fit (a centre crop) or by the tile.
    lost: int
    #: Objects below the size this model can see.
    too_small: int


class InputPreview(BaseModel):
    plan: InputPlan
    colours: dict[str, str]
    images: list[PreviewImage]
    skipped: list[str]


def sample(facts: DatasetFacts, profile: ModelProfile, count: int, seed: int) -> list[ImageFacts]:
    """Half the images holding the smallest objects, the rest at random (seeded)."""
    count = max(1, min(count, MAX_PREVIEWS))
    chosen: list[ImageFacts] = []
    for _, annotation in object_sizes(facts, profile):
        image = facts.image(annotation.image_id)
        if image is not None and image not in chosen:
            chosen.append(image)
        if len(chosen) >= count // 2:
            break
    rest = [image for image in facts.images if image not in chosen]
    random.Random(seed).shuffle(rest)
    return chosen + rest[: count - len(chosen)]


def _plan(profile: ModelProfile) -> PreprocessPlan:
    fit = fit_of(profile)
    return PreprocessPlan(
        size=profile.input_size,
        geometry="center-crop" if fit == "center-crop" else "aspect-preserve",
        patch_size=profile.cell_px,
        mean=IMAGENET_MEAN,
        std=IMAGENET_STD,
    )


@dataclass(frozen=True, slots=True)
class _Fitted:
    """The model's picture, and how targets follow it into that picture."""

    image: Image.Image
    #: Doc 10's transform; None for a stretch, which moves x and y by different factors.
    transform: GeometryTransform | None
    scale_x: float = 1.0
    scale_y: float = 1.0

    def boxes(self, boxes: list[Box]) -> tuple[list[Box], list[int]]:
        if self.transform is not None:
            return transform_boxes(self.transform, boxes)
        kept: list[Box] = []
        indices: list[int] = []
        for index, (x, y, w, h) in enumerate(boxes):
            left, top = max(0.0, x * self.scale_x), max(0.0, y * self.scale_y)
            right = min(float(self.image.width), (x + w) * self.scale_x)
            bottom = min(float(self.image.height), (y + h) * self.scale_y)
            if right > left and bottom > top:
                kept.append((left, top, right - left, bottom - top))
                indices.append(index)
        return kept, indices

    def mask(self, mask: Image.Image) -> Image.Image:
        if self.transform is not None:
            return transform_mask(self.transform, mask)
        return mask.resize(self.image.size, Image.Resampling.NEAREST)


def _fit(profile: ModelProfile, image: Image.Image) -> _Fitted:
    fit = fit_of(profile)
    if fit in ("letterbox", "center-crop"):
        return _Fitted(*apply_geometry(_plan(profile), image))
    if fit == "stretch":
        # What a Hugging Face processor does with size {height, width}: the exact size,
        # aspect ratio not kept (RF-DETR, SAM 2).
        size = profile.input_size
        resized = image.resize((size, size), Image.Resampling.BILINEAR)
        return _Fitted(resized, None, size / image.width, size / image.height)
    scale = profile.scale_for(*image.size)
    size_xy = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(size_xy, Image.Resampling.BILINEAR)
    return _Fitted(resized, GeometryTransform(scale, 0.0, 0.0, *size_xy, image.size))


def _tile_for(image: ImageFacts, annotations: list[AnnotationFacts], tiles: int) -> Tile | None:
    """The tile holding the image's smallest object: the one worth looking at."""
    if tiles <= 1:
        return None
    grid = plan_tiles(image.width, image.height, *grid_for(image.width, image.height, tiles))
    if not annotations:
        return grid[0]
    small = min(annotations, key=lambda a: a.width * a.height)
    inside = [t for t in grid if _inside(small, t)]
    return inside[0] if inside else grid[0]


def _inside(annotation: AnnotationFacts, tile: Tile) -> bool:
    cx, cy = annotation.x + annotation.width / 2, annotation.y + annotation.height / 2
    return tile.x <= cx < tile.x + tile.width and tile.y <= cy < tile.y + tile.height


def colours_for(facts: DatasetFacts) -> dict[str, str]:
    names = sorted({a.cls for a in facts.positives()})
    return {name: _colour(i) for i, name in enumerate(names)}


def _colour(index: int) -> str:
    """The palette, then evenly spread hues: chess has 13 classes, and two alike is a lie."""
    if index < len(_PALETTE):
        return _PALETTE[index]
    hue = (index * 0.618034) % 1.0
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.65, 0.95)
    return f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"


def render(
    facts: DatasetFacts,
    profile: ModelProfile,
    image: ImageFacts,
    tiles: int,
    class_map: dict[str, str | None],
) -> PreviewImage:
    """One image as the model gets it, with its targets as training gets them."""
    colours = colours_for(facts)
    annotations = [a for a in facts.positives() if a.image_id == image.id]
    tile = _tile_for(image, annotations, tiles)
    if tile is not None:
        # Objects in the other tiles are not lost: training sees them there.
        annotations = [a for a in annotations if _inside(a, tile)]
    with Image.open(image.path) as source:
        picture = source.convert("RGB")
    offset = (0, 0)
    if tile is not None:
        picture = picture.crop((tile.x, tile.y, tile.x + tile.width, tile.y + tile.height))
        offset = (tile.x, tile.y)
    # A whole-image label has no boxes to learn from, so none are drawn or judged.
    boxes = [a for a in annotations if a.kind == "box" and profile.annotation_kind != "labels"]
    fitted, lost, too_small = fit_and_draw(
        profile,
        picture,
        [(a.cls, a.x - offset[0], a.y - offset[1], a.width, a.height) for a in boxes],
        colours,
    )
    if profile.annotation_kind == "masks" and any(a.kind == "mask" for a in annotations):
        lost += _draw_masks(facts, image, tile, fitted, colours, class_map)
    return PreviewImage(
        path=image.path,
        tile=(tile.x, tile.y, tile.width, tile.height) if tile else None,
        data_url=data_url(fitted.image),
        width=fitted.image.width,
        height=fitted.image.height,
        objects=len(annotations),
        lost=lost,
        too_small=too_small,
    )


def fit_and_draw(
    profile: ModelProfile,
    picture: Image.Image,
    boxes: list[tuple[str, float, float, float, float]],
    colours: dict[str, str],
) -> tuple[_Fitted, int, int]:
    """The picture as the model gets it, with (class, x, y, w, h) boxes drawn on it.
    Returns it with how many boxes the fit lost and how many are too small to see."""
    fitted = _fit(profile, picture)
    draw = ImageDraw.Draw(fitted.image)
    moved, kept = fitted.boxes([box[1:] for box in boxes])
    too_small = 0
    for (x, y, w, h), index in zip(moved, kept, strict=True):
        small = (w * h) ** 0.5 < profile.min_visible_px
        too_small += small
        colour = TOO_SMALL_COLOUR if small else colours.get(boxes[index][0], _PALETTE[0])
        draw.rectangle((x, y, x + w, y + h), outline=colour, width=1 if small else 2)
    return fitted, len(boxes) - len(kept), too_small


def _draw_masks(
    facts: DatasetFacts,
    image: ImageFacts,
    tile: Tile | None,
    fitted: _Fitted,
    colours: dict[str, str],
    class_map: dict[str, str | None],
) -> int:
    """Tint each outline into the picture. Returns how many vanished in the fit."""
    lost = 0
    for mask in MaskStore().masks_for_image(facts.dataset_id, image.path):
        name = normalise_class_name(mask.prompt)
        cls = class_map.get(name, name) if name in class_map else name
        if mask.label != "positive" or cls is None:
            continue
        pixels = rle_decode(mask.rle.counts, mask.rle.size).astype(np.uint8)
        if tile is not None:
            pixels = pixels[tile.y : tile.y + tile.height, tile.x : tile.x + tile.width]
        moved = np.asarray(fitted.mask(Image.fromarray(pixels, mode="L"))) == 1
        if not moved.any():
            lost += 1
            continue
        colour = Image.new("RGB", fitted.image.size, colours.get(cls, _PALETTE[0]))
        alpha = Image.fromarray((moved * 110).astype(np.uint8), mode="L")
        fitted.image.paste(colour, (0, 0), alpha)
    return lost


def data_url(picture: Image.Image) -> str:
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


__all__ = [
    "MAX_PREVIEWS",
    "InputPreview",
    "PreviewImage",
    "colours_for",
    "data_url",
    "fit_and_draw",
    "render",
    "sample",
]
