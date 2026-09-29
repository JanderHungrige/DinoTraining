"""Handling unequal classes during training (doc 86).

A model rewards itself for being right often. When one class has 12 times the examples of
another (blood cells: red cells against platelets), it can score well while mostly ignoring
the rare class. There are two remedies, and the choice between them is doc 86's planner's:

* **`weighted-loss`**: a mistake on a rare class costs more. The weight is the square root
  of the inverse frequency, normalised to a mean of 1 and capped at `MAX_WEIGHT`. The full
  inverse over-corrects: at 50× the rare class dominates and the model starts to see it
  everywhere.
* **`balanced-sampling`**: images holding rare classes are shown more often. This is
  repeat-factor sampling (Gupta et al., LVIS 2019). Each class gets `sqrt(f_max / f_c)`,
  where `f` is the share of images containing it; each image takes the largest factor
  among its classes; and stochastic rounding turns the fractional part into an occasional
  extra visit. It suits detection, where a weighted loss fights the thousands of
  background cells in every image.

`none` leaves training exactly as it was. That matters: a stored head's provenance names
the procedure that trained it.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Literal

import torch

from app.ml.heads.registry import HeadTypeSpec
from app.ml.training.losses import LossFn, loss_for
from app.ml.training.samples import TrainingSample

Strategy = Literal["none", "weighted-loss", "balanced-sampling"]
STRATEGIES: tuple[Strategy, ...] = ("none", "weighted-loss", "balanced-sampling")

#: No class costs more than this many times the average. Beyond it, a class with three
#: examples would outweigh everything else put together.
MAX_WEIGHT = 10.0
#: No image is shown more than this many times per epoch.
MAX_REPEAT = 10.0


def class_weights(counts: Sequence[int]) -> list[float]:
    """Square-root inverse frequency, mean 1 over the classes present, capped.

    A class with no examples keeps weight 1: there is nothing to weight, and an infinite
    weight on an absent class would only matter the first time it appeared.
    """
    present = [c for c in counts if c > 0]
    if not present:
        return [1.0] * len(counts)
    raw = [1.0 / math.sqrt(c) if c > 0 else 0.0 for c in counts]
    mean = sum(raw) / len(present)
    return [min(MAX_WEIGHT, r / mean) if c > 0 else 1.0 for r, c in zip(raw, counts, strict=True)]


def repeat_factors(presence: Sequence[Iterable[int]]) -> list[float]:
    """Per image: the largest `sqrt(f_max / f_c)` among the classes it holds (≥ 1)."""
    sets = [set(classes) for classes in presence]
    images_with: dict[int, int] = {}
    for classes in sets:
        for cls in classes:
            images_with[cls] = images_with.get(cls, 0) + 1
    if not images_with:
        return [1.0] * len(sets)
    most = max(images_with.values())
    per_class = {cls: min(MAX_REPEAT, math.sqrt(most / n)) for cls, n in images_with.items()}
    return [max((per_class[c] for c in classes), default=1.0) for classes in sets]


def epoch_indices(
    indices: Sequence[int], factors: Sequence[float], rng: random.Random
) -> tuple[int, ...]:
    """One epoch's visits: each index `floor(r)` times, plus once more with probability
    `r - floor(r)`, in shuffled order. `factors` is indexed like the cache, not like
    `indices`."""
    visits: list[int] = []
    for index in indices:
        factor = factors[index]
        whole = int(factor)
        visits.extend([index] * (whole + (1 if rng.random() < factor - whole else 0)))
    rng.shuffle(visits)
    return tuple(visits)


def sample_classes(sample: TrainingSample, task: str) -> set[int]:
    """The classes a sample holds, in the head's vocabulary. Segmentation's +1 is the
    background class `classes_for_task` puts in front."""
    return set(sample_instances(sample, task))


def sample_instances(sample: TrainingSample, task: str) -> Counter[int]:
    """How many of each class a sample holds: what the loss adds up, one term per object
    (per image for classification)."""
    if task == "classification":
        return Counter() if sample.image_class is None else Counter([sample.image_class])
    if task == "segmentation":
        return Counter(mask.class_index + 1 for mask in sample.masks)
    return Counter(target[0] for target in sample.targets)


def class_counts(
    samples: Sequence[TrainingSample], indices: Sequence[int], task: str, size: int
) -> list[int]:
    """Objects per class over the training indices only: validation must not steer it.

    Objects, not images: in blood cells the platelets are in 201 of 364 pictures, but
    number 361 against 4,153 red cells. Counted by image the two look nearly equal and
    the weights come out flat (measured live, 2026-09-29).
    """
    counts = [0] * size
    for index in indices:
        for cls, n in sample_instances(samples[index], task).items():
            if 0 <= cls < size:
                counts[cls] += n
    return counts


@dataclass(frozen=True)
class Balance:
    """What a run does about unequal classes, decided once before the first epoch."""

    loss: LossFn
    #: Per cache index; None unless sampling is balanced.
    factors: list[float] | None
    seed: int

    def order(self, train: Sequence[int], epoch: int) -> tuple[int, ...]:
        if self.factors is None:
            return tuple(train)
        return epoch_indices(train, self.factors, random.Random(self.seed * 1000 + epoch))


def plan_balance(
    strategy: str,
    spec: HeadTypeSpec,
    samples: Sequence[TrainingSample],
    train: Sequence[int],
    num_classes: int,
    seed: int,
) -> Balance:
    """`samples` must line up with the indices training uses (the cache or the live pass)."""
    if strategy == "weighted-loss":
        counts = class_counts(samples, train, spec.task, num_classes)
        if spec.task == "segmentation" and counts:
            counts[0] = max(counts)  # background is never the rare class
        return Balance(weighted_loss(spec, class_weights(counts)), None, seed)
    if strategy == "balanced-sampling":
        presence = [sample_classes(sample, spec.task) for sample in samples]
        return Balance(loss_for(spec), repeat_factors(presence), seed)
    return Balance(loss_for(spec), None, seed)


def weighted_loss(spec: HeadTypeSpec, weights: Sequence[float]) -> LossFn:
    """The head type's loss with per-class weights bound in."""
    return partial(loss_for(spec), class_weights=torch.tensor(list(weights)))  # type: ignore[call-arg]


__all__ = [
    "Balance",
    "plan_balance",
    "MAX_REPEAT",
    "MAX_WEIGHT",
    "STRATEGIES",
    "Strategy",
    "class_counts",
    "class_weights",
    "epoch_indices",
    "sample_instances",
    "repeat_factors",
    "sample_classes",
    "weighted_loss",
]
