"""Which augmentation preset, and what it does to a real picture (doc 87).

The domain cannot be measured, so the recommendation is a guess from the class names,
and it says so. The preview is what settles it: one of the dataset's own pictures, shown
as the model gets it, next to changed versions, each with its boxes moved by the same
code training uses.
"""

from __future__ import annotations

import random

from PIL import Image
from pydantic import BaseModel

from app.cloud.pictures import ensure_local
from app.ml.augment import PRESETS, Variant, augment, meaning_guard
from app.prep.input_preview import PreviewImage, colours_for, data_url, fit_and_draw, sample
from app.prep.profiles import ModelProfile
from app.prep.stats import DatasetFacts

#: Words in class names that suggest a domain. First match wins, in this order.
DOMAIN_WORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("microscopy", ("cell", "rbc", "wbc", "platelet", "bacteri", "nucle", "tissue", "cyte")),
    ("documents", ("text", "word", "table", "page", "stamp", "signature", "paragraph")),
    ("outdoor", ("car", "road", "rail", "track", "train", "signal", "pedestrian", "traffic",
                 "vehicle", "vegetation", "tree", "bike", "truck", "bus")),
    ("indoor", ("chess", "pawn", "bishop", "product", "bottle", "cup", "chair", "shelf")),
)  # fmt: skip


class PresetInfo(BaseModel):
    id: str
    title: str
    explained: str
    #: Flips and turns this preset would use, left out because of `guarded_classes`.
    guarded: bool


class AugmentationPlan(BaseModel):
    recommended: str
    reason: str
    presets: list[PresetInfo]
    guarded_classes: list[str]
    #: False while this target's training path does not augment yet (doc 90).
    applies_to_training: bool


class AugmentationPreview(BaseModel):
    preset: str
    #: The original first, then the changed versions.
    images: list[PreviewImage]
    guarded_classes: list[str]


def _classes(facts: DatasetFacts) -> list[str]:
    return sorted({a.cls for a in facts.positives()})


def recommend(names: list[str]) -> tuple[str, str]:
    for preset, words in DOMAIN_WORDS:
        hits = [n for n in names if any(word in n.lower() for word in words)]
        if hits:
            return preset, (
                f"A guess from the class names ({', '.join(hits[:3])}): "
                f"{PRESETS[preset].title.lower()}. Look at the preview, and pick another "
                "if your pictures are different."
            )
    return "general", (
        "The class names do not suggest a particular kind of picture, so the general "
        "preset. Look at the preview, and pick one closer to your pictures if there is one."
    )


def plan_augmentation(facts: DatasetFacts, profile: ModelProfile) -> AugmentationPlan:
    names = _classes(facts)
    recommended, reason = recommend(names)
    _, risky = meaning_guard(PRESETS["general"], names)
    presets = [
        PresetInfo(
            id=preset.id,
            title=preset.title,
            explained=preset.explained,
            guarded=bool(meaning_guard(preset, names)[1]),
        )
        for preset in PRESETS.values()
    ]
    if risky:
        reason += (
            f" Mirroring is left out because of {', '.join(risky[:3])}: mirrored, it may "
            "mean something else."
        )
    return AugmentationPlan(
        recommended=recommended,
        reason=reason,
        presets=presets,
        guarded_classes=risky,
        applies_to_training=profile.id.startswith("head-"),
    )


def preview_augmentation(
    facts: DatasetFacts, profile: ModelProfile, preset_id: str, count: int, seed: int
) -> AugmentationPreview:
    """One picture, as the model gets it: the original, then `count` changed versions."""
    if preset_id not in PRESETS:
        raise ValueError(f"Unknown augmentation preset: {preset_id}")
    names = _classes(facts)
    preset, risky = meaning_guard(PRESETS[preset_id], names)
    colours = colours_for(facts)
    chosen = sample(facts, profile, 1, seed)
    if not chosen:
        raise ValueError("The dataset has no images to preview.")
    image = chosen[0]
    boxes = [a for a in facts.positives() if a.image_id == image.id and a.kind == "box"]
    with Image.open(ensure_local(image.path)) as source:
        picture = source.convert("RGB")
    original = Variant(picture, [(a.x, a.y, a.width, a.height) for a in boxes], [])
    rng = random.Random(seed)
    versions = [original] + [augment(original, preset, rng) for _ in range(count)]
    images = []
    for version in versions:
        drawn = [(a.cls, *box) for a, box in zip(boxes, version.boxes, strict=True)]
        if profile.annotation_kind == "labels":
            drawn = []
        fitted, lost, too_small = fit_and_draw(profile, version.image, drawn, colours)
        images.append(
            PreviewImage(
                path=image.path,
                tile=None,
                data_url=data_url(fitted.image),
                width=fitted.image.width,
                height=fitted.image.height,
                objects=len(boxes),
                lost=lost,
                too_small=too_small,
            )
        )
    return AugmentationPreview(preset=preset.id, images=images, guarded_classes=risky)


__all__ = ["AugmentationPlan", "AugmentationPreview", "plan_augmentation", "preview_augmentation"]
