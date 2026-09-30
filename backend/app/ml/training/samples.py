"""Turning stored annotations into training targets.

Wave 1 stored boxes labelled positive/negative/unclear with a prompt, and every head's
targets are *derived* here — the derivation rules being the interesting part, because
each one is a choice about what the user meant:

* ``positive``  → a target.
* ``negative``  → not a target. The user said "this is not the object", which makes the
  region legitimate background rather than something to ignore.
* ``unclear``   → neither. Cells it covers are ignored by the loss. Forcing them to
  background would train the model to suppress exactly the cases a human could not call.

**Masks are read here too now.** Doc 61 gave the Annotation Studio somewhere to put a
segmentation, and until then `linear-segmenter` was registered `trainable=True` with a
loss and metrics wired to it and nothing that could produce the target it reads — a run
raised `KeyError: 'mask'` on the first batch. The three verdicts mean exactly what they
mean for a box, which is the point: a reviewer marking masks is making the same three
judgements, so one set of rules serves both.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.datasets.class_names import UNNAMED_CLASS as UNNAMED_CLASS  # re-exported
from app.datasets.masks import MaskStore
from app.datasets.models import Box, Mask
from app.datasets.store import DatasetStore
from app.ml.training.sample_prep import load_preparation, prepared_rows
from app.ml.training.vocabulary import (
    build_class_vocabulary as build_class_vocabulary,  # re-exported
)
from app.ml.training.vocabulary import build_mask_vocabulary as build_mask_vocabulary  # re-exported
from app.ml.training.vocabulary import class_name

logger = logging.getLogger(__name__)

#: Index 0 of a segmentation vocabulary. A segmenter must be able to predict "none of the
#: above" for every pixel that is not an object, and most pixels are not — without it the
#: loss can only ignore them, and the model learns to label the whole frame.
BACKGROUND_CLASS = "background"


@dataclass(frozen=True, slots=True)
class MaskTarget:
    """One stored mask, kept as run lengths rather than pixels.

    **Not rasterised here.** A 2464x1600 label map is 3.9 MB, and a sample set spans the
    whole dataset — the OSDaR23 rail set alone would be 1.5 GB held in memory before a
    single batch. The RLE is roughly 13 KB, and `build_targets` decodes one image's worth
    at the moment it needs it.

    `class_index` is into `SampleSet.class_names`, which has **no** background entry. The
    segmentation target adds one, because 0 has to mean background there — see
    `classes_for_task`.
    """

    class_index: int
    #: (height, width) — COCO's order.
    size: tuple[int, int]
    counts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class TrainingSample:
    """One image and the annotations that supervise it."""

    path: str
    width: int
    height: int
    #: (class_index, x, y, w, h) for positive boxes only.
    targets: tuple[tuple[int, float, float, float, float], ...] = ()
    #: Regions the loss must ignore — from ``unclear`` boxes.
    ignore_regions: tuple[tuple[float, float, float, float], ...] = ()
    #: Single class index for classification, or None when it could not be derived.
    image_class: int | None = None
    #: Positive masks, for a segmentation head. Empty for a box-only dataset.
    masks: tuple[MaskTarget, ...] = ()
    #: Masks the loss must ignore — from ``unclear``. Same rule as `ignore_regions`, and
    #: it matters more here: an uncertain *region* is a large share of the pixels.
    ignore_masks: tuple[MaskTarget, ...] = ()
    #: True when *any* mask was stored for this image, whatever its verdict.
    #:
    #: This is the difference between "a reviewer looked and there was nothing" and
    #: "nobody segmented this picture", which are identical if you only count positives.
    #: An all-background frame is real supervision; an unsegmented one teaches a segmenter
    #: that whatever is in it is background. Rejecting a mask keeps it as a `negative`
    #: precisely so the trainer can tell — see the Dataset Generator's own hint.
    segmented: bool = False
    #: The stored split side (doc 84), used when training from a recipe (doc 90).
    split: str | None = None
    #: A tile of the image, (x, y, width, height), when training on tiles (doc 90).
    crop: tuple[int, int, int, int] | None = None


@dataclass
class SampleSet:
    """Samples plus the vocabulary they were built against."""

    samples: list[TrainingSample] = field(default_factory=list)
    #: Classes carried by positive **boxes**. What a detector or classifier learns.
    class_names: tuple[str, ...] = ()
    #: Classes carried by positive **masks**. What a segmenter learns, and deliberately
    #: not merged with the boxes' — see `build_mask_vocabulary`.
    mask_class_names: tuple[str, ...] = ()
    #: Images skipped for classification because they named more than one class.
    mixed_class_images: int = 0

    @property
    def num_classes(self) -> int:
        return len(self.class_names)


def learnable_classes(sample_set: SampleSet, task: str) -> tuple[str, ...]:
    """The dataset-derived classes a head of this task can actually learn.

    Kept apart from `classes_for_task` because background is *not* one of these: a
    segmentation vocabulary of background alone means the dataset taught nothing, and a
    guard reading the prefixed list would see one class and let the run proceed.
    """
    return sample_set.mask_class_names if task == "segmentation" else sample_set.class_names


def classes_for_task(sample_set: SampleSet, task: str) -> tuple[str, ...]:
    """The vocabulary a head of this task is actually built against.

    **Segmentation reads the mask classes, and gets a background class in front of them.**

    Every pixel of a segmentation belongs to some class, and most belong to none of the
    annotated ones; without an explicit background the loss can only ignore those pixels,
    and a model that never sees background learns to label the entire frame. Detection has
    no such problem — a cell with no box is simply not a positive.

    Index 0, deliberately, and worth knowing why beyond convention: the overlay registry
    already treats `class_names[0] === 'background'` as the signal to draw class 0
    transparent. A head trained here therefore renders correctly in the Inference Viewer
    without anything being told about it.
    """
    if task == "segmentation":
        return (BACKGROUND_CLASS, *sample_set.mask_class_names)
    return sample_set.class_names


def build_samples(
    store: DatasetStore, dataset_ids: tuple[str, ...], masks: MaskStore | None = None
) -> SampleSet:
    """Read the given datasets and derive per-image training samples.

    Boxes and masks are read separately and joined by **image id**, not by path: the same
    file can appear in several datasets, and `image_annotations` already returns the id.
    """
    mask_store = masks or MaskStore()

    annotations: list[tuple[int, str, int, int, list[Box]]] = []
    stored_masks: list[tuple[int, str, int, int, list[Mask]]] = []
    splits: dict[int, str] = {}
    for dataset_id in dataset_ids:
        # Doc 90: excluded images left out, the class map applied, the stored split read.
        prep = load_preparation(dataset_id, store.settings)
        annotations.extend(prepared_rows(store.image_annotations(dataset_id), prep))
        stored_masks.extend(prepared_rows(mask_store.image_masks(dataset_id), prep))
        splits.update(prep.split)

    masks_by_image = {image_id: image_masks for image_id, _, _, _, image_masks in stored_masks}

    class_names = build_class_vocabulary(annotations)
    mask_class_names = build_mask_vocabulary(stored_masks)
    index_of = {name: index for index, name in enumerate(class_names)}
    mask_index_of = {name: index for index, name in enumerate(mask_class_names)}

    samples: list[TrainingSample] = []
    mixed = 0

    for image_id, path, width, height, boxes in annotations:
        targets: list[tuple[int, float, float, float, float]] = []
        ignore: list[tuple[float, float, float, float]] = []
        present: set[int] = set()

        for box in boxes:
            if box.label == "positive":
                class_index = index_of[class_name(box)]
                targets.append((class_index, box.x, box.y, box.w, box.h))
                present.add(class_index)
            elif box.label == "unclear":
                ignore.append((box.x, box.y, box.w, box.h))
            # `negative` deliberately contributes nothing: the region is background.

        # Classification needs exactly one class per image. Mixed images are skipped and
        # counted rather than silently resolved — picking the first class would train on
        # a label the user never gave. Multi-label is out of scope for this wave.
        image_class: int | None = None
        if len(present) == 1:
            image_class = next(iter(present))
        elif len(present) > 1:
            mixed += 1

        positive_masks: list[MaskTarget] = []
        ignored_masks: list[MaskTarget] = []
        image_masks = masks_by_image.get(image_id, [])
        for mask in image_masks:
            target = MaskTarget(
                # Into the **mask** vocabulary, which is why it is a separate lookup: a
                # box index would point at a different class, or at none.
                class_index=mask_index_of.get(class_name(mask), 0),
                size=mask.rle.size,
                counts=tuple(mask.rle.counts),
            )
            if mask.label == "positive":
                positive_masks.append(target)
            elif mask.label == "unclear":
                ignored_masks.append(target)
            # `negative` contributes nothing, exactly as for a box: the reviewer said the
            # region is *not* the thing, which makes it legitimate background.

        samples.append(
            TrainingSample(
                path=path,
                width=width,
                height=height,
                targets=tuple(targets),
                ignore_regions=tuple(ignore),
                image_class=image_class,
                masks=tuple(positive_masks),
                ignore_masks=tuple(ignored_masks),
                segmented=bool(image_masks),
                split=splits.get(image_id),
            )
        )

    if mixed:
        logger.info("%d image(s) name more than one class and cannot train classification", mixed)

    return SampleSet(
        samples=samples,
        class_names=class_names,
        mask_class_names=mask_class_names,
        mixed_class_images=mixed,
    )


def samples_for_task(sample_set: SampleSet, task: str) -> list[TrainingSample]:
    """The subset a given task can actually learn from.

    Classification drops images without a single derived class. Dense tasks keep
    everything, including images with no positives — a pure-background image is real
    supervision for a detector, not an empty sample.
    """
    if task == "classification":
        return [sample for sample in sample_set.samples if sample.image_class is not None]
    if task == "segmentation":
        # Segmentation drops what nobody segmented — not what came back empty. An image
        # whose masks were all rejected is a genuine all-background frame and trains; an
        # image that only ever had boxes is one nobody looked at with a segmenter, and
        # training on it teaches that whatever is in it is background. Counting positives
        # cannot tell those apart, which is what `segmented` is for.
        return [sample for sample in sample_set.samples if sample.segmented]
    return list(sample_set.samples)
