"""Turning Wave 1's box annotations into training targets.

Wave 1 stores boxes labelled positive/negative/unclear with a prompt. That is
box-shaped data, so every head's targets are *derived* here — and the derivation rules
are the interesting part, because each one is a choice about what the user meant:

* ``positive``  → a target.
* ``negative``  → not a target. The user said "this is not the object", which makes the
  region legitimate background rather than something to ignore.
* ``unclear``   → neither. Cells it covers are ignored by the loss. Forcing them to
  background would train the model to suppress exactly the cases a human could not call.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.datasets.models import Box
from app.datasets.store import DatasetStore

logger = logging.getLogger(__name__)

#: Prompt used when a positive box carries none, so it still forms a usable class.
UNNAMED_CLASS = "object"


@dataclass(frozen=True, slots=True)
class TrainingSample:
    """One image and the boxes that supervise it."""

    path: str
    width: int
    height: int
    #: (class_index, x, y, w, h) for positive boxes only.
    targets: tuple[tuple[int, float, float, float, float], ...] = ()
    #: Regions the loss must ignore — from ``unclear`` boxes.
    ignore_regions: tuple[tuple[float, float, float, float], ...] = ()
    #: Single class index for classification, or None when it could not be derived.
    image_class: int | None = None


@dataclass
class SampleSet:
    """Samples plus the vocabulary they were built against."""

    samples: list[TrainingSample] = field(default_factory=list)
    class_names: tuple[str, ...] = ()
    #: Images skipped for classification because they named more than one class.
    mixed_class_images: int = 0

    @property
    def num_classes(self) -> int:
        return len(self.class_names)


def _class_name(box: Box) -> str:
    """A positive box's class is its prompt, normalised."""
    prompt = (box.prompt or "").strip().lower().rstrip(".")
    return prompt or UNNAMED_CLASS


def build_class_vocabulary(
    annotations: list[tuple[int, str, int, int, list[Box]]],
) -> tuple[str, ...]:
    """Distinct classes across all positive boxes, **sorted**.

    Sorted for determinism. A class order that shifts between runs makes saved weights
    uninterpretable — index 3 would mean a different thing than it did at training time,
    and nothing about the checkpoint would reveal it.
    """
    names = {
        _class_name(box)
        for _, _, _, _, boxes in annotations
        for box in boxes
        if box.label == "positive"
    }
    return tuple(sorted(names))


def build_samples(
    store: DatasetStore, dataset_ids: tuple[str, ...]
) -> SampleSet:
    """Read the given datasets and derive per-image training samples."""
    annotations: list[tuple[int, str, int, int, list[Box]]] = []
    for dataset_id in dataset_ids:
        annotations.extend(store.image_annotations(dataset_id))

    class_names = build_class_vocabulary(annotations)
    index_of = {name: index for index, name in enumerate(class_names)}

    samples: list[TrainingSample] = []
    mixed = 0

    for _, path, width, height, boxes in annotations:
        targets: list[tuple[int, float, float, float, float]] = []
        ignore: list[tuple[float, float, float, float]] = []
        present: set[int] = set()

        for box in boxes:
            if box.label == "positive":
                class_index = index_of[_class_name(box)]
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

        samples.append(
            TrainingSample(
                path=path,
                width=width,
                height=height,
                targets=tuple(targets),
                ignore_regions=tuple(ignore),
                image_class=image_class,
            )
        )

    if mixed:
        logger.info("%d image(s) name more than one class and cannot train classification", mixed)

    return SampleSet(samples=samples, class_names=class_names, mixed_class_images=mixed)


def samples_for_task(sample_set: SampleSet, task: str) -> list[TrainingSample]:
    """The subset a given task can actually learn from.

    Classification drops images without a single derived class. Dense tasks keep
    everything, including images with no positives — a pure-background image is real
    supervision for a detector, not an empty sample.
    """
    if task == "classification":
        return [sample for sample in sample_set.samples if sample.image_class is not None]
    return list(sample_set.samples)
