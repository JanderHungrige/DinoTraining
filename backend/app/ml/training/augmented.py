"""Augmentation in training: changed copies of the training images (doc 87).

The frozen backbone's feature cache (doc 11) computes each image's features once. An
augmented image is a different image, so it needs its own features: this caches
`copies` changed versions of every **training** image next to the originals, and each
round shows each training image as one of its versions, chosen at random. Validation and
test images are never augmented; a score on changed pictures would measure the changes.

The live path (backbone training too, doc 55) recomputes features every step anyway, so
it simply augments each image as it loads it (`augment_sample`).

**Memory is the limit, and it is said out loud.** A DINOv2-small feature map at 448 px is
about 1.5 MB, so 300 training images with 3 copies each is 1.4 GB. The number of copies
is reduced to fit `CACHE_BUDGET_BYTES`, and the job says by how much.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

import numpy as np
from PIL import Image

from app.datasets.rle import rle_decode, rle_encode
from app.ml.augment import PRESETS, Preset, Variant, augment, meaning_guard
from app.ml.backbone import Backbone, extract
from app.ml.heads.registry import HeadTypeSpec
from app.ml.preprocess import PreprocessPlan, apply_geometry, to_pixel_values
from app.ml.training.loop import CachedSample, build_targets, load_image, to_device
from app.ml.training.samples import MaskTarget, TrainingSample

logger = logging.getLogger(__name__)

CACHE_BUDGET_BYTES = 3 * 1024**3
DEFAULT_COPIES = 2


def _masks(targets: Sequence[MaskTarget]) -> list[np.ndarray]:
    return [rle_decode(list(t.counts), t.size) for t in targets]


def _encoded(templates: Sequence[MaskTarget], masks: list[np.ndarray]) -> tuple[MaskTarget, ...]:
    out = []
    for template, mask in zip(templates, masks, strict=True):
        counts, size = rle_encode(np.ascontiguousarray(mask, dtype=bool))
        out.append(MaskTarget(class_index=template.class_index, size=size, counts=tuple(counts)))
    return tuple(out)


def augment_sample(
    image: Image.Image, sample: TrainingSample, preset: Preset, rng: random.Random
) -> tuple[Image.Image, TrainingSample]:
    """A changed image and the same sample with every target moved as the image was.

    Boxes, ignore regions, masks and ignore masks all go through one `augment` call, so
    no target can be left behind by an operation the others received.
    """
    n_boxes, n_ignore = len(sample.targets), len(sample.ignore_regions)
    boxes = [t[1:] for t in sample.targets] + list(sample.ignore_regions)
    masks = _masks(sample.masks) + _masks(sample.ignore_masks)
    changed = augment(Variant(image, boxes, masks), preset, rng)
    n_masks = len(sample.masks)
    moved = replace(
        sample,
        width=changed.image.width,
        height=changed.image.height,
        targets=tuple(
            (t[0], *b) for t, b in zip(sample.targets, changed.boxes[:n_boxes], strict=True)
        ),
        ignore_regions=tuple(changed.boxes[n_boxes : n_boxes + n_ignore]),
        masks=_encoded(sample.masks, changed.masks[:n_masks]),
        ignore_masks=_encoded(sample.ignore_masks, changed.masks[n_masks:]),
    )
    return changed.image, moved


def preset_for(name: str, class_names: Sequence[str]) -> tuple[Preset, list[str]]:
    """The named preset with the meaning guard applied; raises for an unknown name."""
    if name not in PRESETS:
        raise ValueError(f"Unknown augmentation preset: {name}")
    return meaning_guard(PRESETS[name], list(class_names))


@dataclass
class Variants:
    """Cache indices of each training image's changed copies."""

    of: dict[int, list[int]] = field(default_factory=dict)
    copies: int = 0
    note: str = ""

    def pick(self, order: Sequence[int], rng: random.Random) -> tuple[int, ...]:
        """Each visit shows the original or one of its copies, at random."""
        return tuple(rng.choice([index, *self.of.get(index, [])]) for index in order)


def copies_that_fit(cache: Sequence[CachedSample], train: int, wanted: int) -> int:
    if not cache or train == 0:
        return 0
    features = cache[0][0]
    each = sum(t.element_size() * t.nelement() for t in (features.cls, features.patches))
    used = each * len(cache)
    return max(0, min(wanted, int((CACHE_BUDGET_BYTES - used) // max(1, each * train))))


def cache_variants(
    backbone: Backbone,
    plan: PreprocessPlan,
    spec: HeadTypeSpec,
    samples: Sequence[TrainingSample],
    cache: list[CachedSample],
    train: Sequence[int],
    num_classes: int,
    preset: Preset,
    wanted: int,
    seed: int,
) -> Variants:
    """Append changed copies of the training images to `cache`. `samples[i]` must be the
    sample behind `cache[i]`."""
    copies = copies_that_fit(cache, len(train), wanted)
    variants = Variants(copies=copies)
    if copies < wanted:
        variants.note = f"{copies} of {wanted} augmented copies per image fit in memory."
        logger.info(variants.note)
    rng = random.Random(seed)
    for index in train:
        image = load_image(samples[index].path)
        if image is None:
            continue
        for _ in range(copies):
            changed, sample = augment_sample(image, samples[index], preset, rng)
            resized, transform = apply_geometry(plan, changed)
            features = extract(backbone, to_pixel_values(plan, [resized]))
            targets = build_targets(
                spec, sample, transform, features.grid, plan.patch_size, num_classes
            )
            variants.of.setdefault(index, []).append(len(cache))
            cache.append((features, to_device(targets, features.cls.device)))
    return variants


__all__ = [
    "CACHE_BUDGET_BYTES",
    "DEFAULT_COPIES",
    "Variants",
    "augment_sample",
    "cache_variants",
    "copies_that_fit",
    "preset_for",
]
