"""Augmentation presets that never move a picture without moving its targets (doc 87).

A model shown the same few hundred pictures every round learns those pictures. Showing
each one slightly changed (brighter, blurred, mirrored, cropped) teaches it what stays
the same, which is the object. Two rules make that safe:

1. **Geometry moves the targets with the picture.** A flip, a quarter turn or a crop is
   applied to the image, its boxes and its masks by the same operation, here and nowhere
   else. A crop never cuts an object: one that would is not taken.
2. **Nothing that changes meaning.** A mirrored "left arrow" is a right arrow, and a
   mirrored rail signal stands on the wrong side of the track. Presets for such domains
   carry no flips, and any preset drops them when a class name suggests text, signs or
   sides (`meaning_guard`).

Pure functions over PIL images and numpy masks; a seeded `random.Random` makes every
variant reproducible.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, replace

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

Box = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class Preset:
    id: str
    title: str
    explained: str
    hflip: float = 0.0
    vflip: float = 0.0
    rot90: bool = False
    #: Smallest crop side as a share of the picture; 1.0 = no crop.
    crop: float = 1.0
    #: Brightness/contrast/saturation vary by up to this share.
    colour: float = 0.0
    blur: float = 0.0
    noise: float = 0.0

    @property
    def geometric(self) -> bool:
        return self.hflip > 0 or self.vflip > 0 or self.rot90 or self.crop < 1.0


PRESETS: dict[str, Preset] = {
    p.id: p
    for p in (
        Preset("none", "No changes", "Every picture is shown as it is."),
        Preset(
            "general",
            "General photos",
            "Mirrored left-right, cropped a little, lighting varied. A safe start for "
            "everyday objects.",
            hflip=0.5,
            crop=0.8,
            colour=0.2,
            blur=0.1,
        ),
        Preset(
            "outdoor",
            "Outdoor, road and rail",
            "Lighting and weather varied strongly, slight blur and grain. Never mirrored: "
            "traffic and signals have a side.",
            crop=0.85,
            colour=0.35,
            blur=0.3,
            noise=0.02,
        ),
        Preset(
            "indoor",
            "Indoor and products",
            "Mirrored left-right, cropped a little, lighting varied moderately.",
            hflip=0.5,
            crop=0.8,
            colour=0.25,
            blur=0.1,
        ),
        Preset(
            "microscopy",
            "Microscopy and top-down",
            "Turned and mirrored in every direction (a cell has no up), staining varied "
            "slightly, occasionally out of focus.",
            hflip=0.5,
            vflip=0.5,
            rot90=True,
            colour=0.15,
            blur=0.2,
        ),
        Preset(
            "documents",
            "Documents and text",
            "Contrast, blur and grain varied as a scanner or camera would. Never mirrored "
            "or turned: text read backwards is not text.",
            crop=0.9,
            colour=0.15,
            blur=0.2,
            noise=0.02,
        ),
    )
}

#: Words in a class name that make a mirror or a turn change what the object is.
MEANING_WORDS = (
    "sign", "text", "letter", "digit", "number", "arrow", "left", "right",
    "word", "plate", "label", "signal", "clock",
)  # fmt: skip


def _words(name: str) -> set[str]:
    """Whole words, singular: "stop signs" → {"stop", "sign"}. Whole words, because
    "platelets" contains "plate" (found live on the blood-cell set, 2026-09-30)."""
    words = {w for w in re.split(r"[^a-z]+", name.lower()) if w}
    return words | {w[:-1] for w in words if w.endswith("s")}


def meaning_guard(preset: Preset, class_names: list[str]) -> tuple[Preset, list[str]]:
    """The preset without flips and turns if a class's meaning depends on its side."""
    risky = [n for n in class_names if _words(n) & set(MEANING_WORDS)]
    if not risky or not (preset.hflip or preset.vflip or preset.rot90):
        return preset, []
    return replace(preset, hflip=0.0, vflip=0.0, rot90=False), risky


@dataclass
class Variant:
    image: Image.Image
    boxes: list[Box]
    masks: list[np.ndarray]


def _flip(v: Variant, horizontal: bool) -> Variant:
    w, h = v.image.size
    method = Image.Transpose.FLIP_LEFT_RIGHT if horizontal else Image.Transpose.FLIP_TOP_BOTTOM
    boxes = [
        (w - x - bw, y, bw, bh) if horizontal else (x, h - y - bh, bw, bh)
        for x, y, bw, bh in v.boxes
    ]
    masks = [np.fliplr(m) if horizontal else np.flipud(m) for m in v.masks]
    return Variant(v.image.transpose(method), boxes, masks)


def _turn(v: Variant) -> Variant:
    """A quarter turn anticlockwise: (x, y) → (y, W - x)."""
    w, _ = v.image.size
    boxes = [(y, w - x - bw, bh, bw) for x, y, bw, bh in v.boxes]
    masks = [np.rot90(m) for m in v.masks]
    return Variant(v.image.transpose(Image.Transpose.ROTATE_90), boxes, masks)


def _crop(v: Variant, smallest: float, rng: random.Random) -> Variant:
    """A random crop that keeps every object whole, or no crop if none does in 10 tries."""
    w, h = v.image.size
    for _ in range(10):
        side = rng.uniform(smallest, 1.0)
        cw, ch = max(1, round(w * side)), max(1, round(h * side))
        left, top = rng.randint(0, w - cw), rng.randint(0, h - ch)
        if all(
            x >= left and y >= top and x + bw <= left + cw and y + bh <= top + ch
            for x, y, bw, bh in v.boxes
        ):
            return Variant(
                v.image.crop((left, top, left + cw, top + ch)),
                [(x - left, y - top, bw, bh) for x, y, bw, bh in v.boxes],
                [m[top : top + ch, left : left + cw] for m in v.masks],
            )
    return v


def _photometric(image: Image.Image, preset: Preset, rng: random.Random) -> Image.Image:
    if preset.colour:
        for enhancer in (ImageEnhance.Brightness, ImageEnhance.Contrast, ImageEnhance.Color):
            image = enhancer(image).enhance(1.0 + rng.uniform(-preset.colour, preset.colour))
    if preset.blur and rng.random() < preset.blur:
        image = image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.5, 1.5)))
    if preset.noise:
        pixels = np.asarray(image, dtype=np.float32)
        grain = np.random.default_rng(rng.randrange(2**32)).normal(
            0, preset.noise * 255, pixels.shape
        )
        image = Image.fromarray(np.clip(pixels + grain, 0, 255).astype(np.uint8))
    return image


def augment(variant: Variant, preset: Preset, rng: random.Random) -> Variant:
    """One changed version. Geometry first (targets follow), then colour (they need not)."""
    if preset.hflip and rng.random() < preset.hflip:
        variant = _flip(variant, horizontal=True)
    if preset.vflip and rng.random() < preset.vflip:
        variant = _flip(variant, horizontal=False)
    if preset.rot90:
        for _ in range(rng.randrange(4)):
            variant = _turn(variant)
    if preset.crop < 1.0:
        variant = _crop(variant, preset.crop, rng)
    image = _photometric(variant.image.convert("RGB"), preset, rng)
    return Variant(image, variant.boxes, variant.masks)


__all__ = ["PRESETS", "Box", "Preset", "Variant", "augment", "meaning_guard"]
