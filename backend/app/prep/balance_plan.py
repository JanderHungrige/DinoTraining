"""Which remedy for unequal classes, and why (doc 86).

The mechanics live in `app.ml.training.imbalance`; this decides between them from the
dataset's numbers and says what each would do *to this dataset*. The effect is computed
with the same functions training uses, so "platelets are shown 3.4× as often" is what
will happen, not an estimate of it.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from app.ml.training.imbalance import Strategy, class_weights, repeat_factors
from app.prep.profiles import ModelProfile
from app.prep.stats import DatasetFacts

#: Largest ÷ smallest class, in examples, up to which classes count as roughly equal.
BALANCED_RATIO = 3.0
#: Below this many examples no remedy helps: the variety is not there to learn from.
TOO_FEW = 10


class ClassBalance(BaseModel):
    name: str
    examples: int
    images: int
    #: Loss weight under "weighted-loss".
    weight: float
    #: Average visits per epoch of an image holding this class, under "balanced-sampling".
    repeat: float


class Option(BaseModel):
    id: str
    title: str
    explained: str


class BalancePlan(BaseModel):
    target: str
    ratio: float
    recommended: Strategy
    reason: str
    classes: list[ClassBalance]
    options: list[Option]
    warnings: list[str]
    #: False while this target's training path does not read the strategy yet (doc 90).
    applies_to_training: bool


OPTIONS = [
    Option(
        id="none",
        title="Leave it",
        explained="Train on the data as it is. Right when the classes are roughly equal.",
    ),
    Option(
        id="weighted-loss",
        title="Make rare classes count more",
        explained="A mistake on a rare class costs the model more than one on a common "
        "class, so it cannot get away with ignoring it. Nothing is repeated, so nothing "
        "is memorised. Best for labelling whole images and for outlines.",
    ),
    Option(
        id="balanced-sampling",
        title="Show rare classes more often",
        explained="Images with rare classes are shown several times per round of training. "
        "Best for boxes, where every image is mostly background and weighting alone is "
        "drowned out.",
    ),
]


def _per_class(facts: DatasetFacts) -> tuple[list[str], Counter[str], list[set[int]]]:
    examples = Counter(a.cls for a in facts.positives())
    names = sorted(examples)
    index = {name: i for i, name in enumerate(names)}
    held: dict[int, set[int]] = {}
    for annotation in facts.positives():
        held.setdefault(annotation.image_id, set()).add(index[annotation.cls])
    return names, examples, [held.get(image.id, set()) for image in facts.images]


#: Below this, showing the rare class's pictures more often barely changes what the
#: model sees: the rare class shares its pictures with the common ones.
USEFUL_REPEAT = 1.5


def _recommend(profile: ModelProfile, ratio: float, rare: ClassBalance) -> tuple[Strategy, str]:
    if ratio <= BALANCED_RATIO:
        return "none", (
            f"The largest class has {ratio:.1f}× the examples of the smallest. That is "
            "close enough to equal that any correction would do more harm than good."
        )
    if profile.task == "detection" and rare.repeat >= USEFUL_REPEAT:
        return "balanced-sampling", (
            f"Classes differ by {ratio:.0f}×, and this model finds boxes. Every picture is "
            "mostly background, which would drown out a weighted loss, so showing the "
            f"pictures with '{rare.name}' more often ({rare.repeat}× per round) works better."
        )
    if profile.task == "detection":
        return "weighted-loss", (
            f"Classes differ by {ratio:.0f}×, but '{rare.name}' appears in {rare.images} "
            "pictures alongside the common classes. Showing those pictures more often would "
            "show the common classes more often too. Counting each "
            f"'{rare.name}' more heavily corrects the balance instead."
        )
    return "weighted-loss", (
        f"Classes differ by {ratio:.0f}×. Making mistakes on rare classes cost more corrects "
        "that without showing the same pictures over and over."
    )


def plan_balance(facts: DatasetFacts, profile: ModelProfile) -> BalancePlan:
    names, examples, presence = _per_class(facts)
    counts = [examples[name] for name in names]
    ratio = max(counts) / min(counts) if counts else 1.0
    # Objects per class, as training counts them (`imbalance.class_counts`), so the weight
    # shown is the weight used.
    weights = class_weights(counts)
    factors = repeat_factors(presence)
    classes = []
    for i, name in enumerate(names):
        holding = [factors[k] for k, held in enumerate(presence) if i in held]
        classes.append(
            ClassBalance(
                name=name,
                examples=examples[name],
                images=len(holding),
                weight=round(weights[i], 2),
                repeat=round(sum(holding) / len(holding), 2) if holding else 1.0,
            )
        )
    rare = min(classes, key=lambda c: c.examples) if classes else None
    recommended, reason = (
        _recommend(profile, ratio, rare) if rare else ("none", "No annotated objects yet.")
    )
    warnings = [
        f"'{c.name}' has only {c.examples} example(s). No setting can invent the variety "
        "that is missing: add more, or merge or leave out this class in the Fix step."
        for c in classes
        if c.examples < TOO_FEW
    ]
    return BalancePlan(
        target=profile.id,
        ratio=round(ratio, 1),
        recommended=recommended,
        reason=reason,
        classes=classes,
        options=OPTIONS,
        warnings=warnings,
        applies_to_training=profile.id.startswith("head-"),
    )


__all__ = ["BALANCED_RATIO", "BalancePlan", "ClassBalance", "plan_balance"]
