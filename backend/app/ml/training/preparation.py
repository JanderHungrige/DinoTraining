"""The prepared-data options a run applies: imbalance (doc 86) and augmentation (doc 87).

Gathered here so `runner._train` asks one question per epoch, "which cache indices, in
which order?", and does not grow a branch per option.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from torch import Tensor, nn

from app.ml.training.augmented import Variants, cache_variants, preset_for
from app.ml.training.config import Split, split_indices
from app.ml.training.imbalance import Balance, plan_balance
from app.ml.training.live_loop import evaluate_live
from app.ml.training.loop import evaluate
from app.ml.training.losses import LossFn
from app.ml.training.tiles import tile_samples

if TYPE_CHECKING:
    from app.ml.backbone import Backbone
    from app.ml.heads.registry import HeadTypeSpec
    from app.ml.preprocess import PreprocessPlan
    from app.ml.training.config import TrainingConfig
    from app.ml.training.job import TrainingJob
    from app.ml.training.live_loop import LivePass
    from app.ml.training.loop import CachedSample
    from app.ml.training.samples import TrainingSample


@dataclass
class Prepared:
    balance: Balance
    variants: Variants
    live: LivePass | None
    seed: int

    def order(self, train: tuple[int, ...], epoch: int) -> tuple[int, ...]:
        """This epoch's visits: balanced first, then each visit as one of its versions."""
        visits = self.balance.order(train, epoch)
        if not self.variants.of:
            return visits
        return self.variants.pick(visits, random.Random(self.seed * 7919 + epoch))

    def rng(self, epoch: int) -> random.Random | None:
        """For the live pass, which augments as it loads."""
        return random.Random(self.seed * 104729 + epoch) if self.live is not None else None


def preset_name(config: TrainingConfig) -> str:
    if config.augmentation == "none" and config.augment:
        return "general"
    return config.augmentation


def prepare(
    job: TrainingJob,
    spec: HeadTypeSpec,
    backbone: Backbone,
    plan: PreprocessPlan,
    usable: list[TrainingSample],
    cache: list[CachedSample],
    live: LivePass | None,
    split: Split,
    num_classes: int,
) -> Prepared:
    """`usable[i]` must be the sample behind `cache[i]` (or the live pass's index i)."""
    config = job.config
    seed = config.split_seed
    balance = plan_balance(config.imbalance, spec, usable, split.train, num_classes, seed)
    preset, risky = preset_for(preset_name(config), job.class_names)
    if risky:
        job.notes.append(
            f"Mirroring and turning were left out: {', '.join(risky[:5])} may mean something "
            "else when mirrored (sides, text or signs)."
        )
    variants = Variants()
    if preset.id != "none":
        if live is None:
            variants = cache_variants(
                backbone, plan, spec, usable, cache, split.train, num_classes, preset,
                config.augment_copies, seed,
            )  # fmt: skip
            if variants.note:
                job.notes.append(variants.note)
        else:
            live = replace(live, augmentation=preset)
    return Prepared(balance, variants, live, seed)


UNPREPARED_NOTE = (
    "Trained without a preparation recipe: the pictures were split at random, so frames of "
    "one video or photos of one scene may sit on both sides and the score may look better "
    "than the model is. The Prepare data tab makes a recipe."
)


def choose_split(job: TrainingJob, usable: Sequence[TrainingSample], total: int) -> Split:
    """The recipe's stored split, or the random one with a note saying so.

    `usable[i]` is the sample behind cache index i. Buffer frames (doc 84) and images
    without a side train nowhere.
    """
    config = job.config
    if config.recipe_id is None:
        job.notes.append(UNPREPARED_NOTE)
        return split_indices(total, config.val_fraction, config.test_fraction, config.split_seed)
    sides: dict[str, list[int]] = {"train": [], "val": [], "test": []}
    for index, sample in enumerate(usable[:total]):
        if sample.split in sides:
            sides[sample.split].append(index)
    if not sides["train"]:
        raise ValueError(
            "The recipe's split has no training pictures. Split the dataset again in the "
            "Prepare data tab and save a new recipe."
        )
    return Split(train=tuple(sides["train"]), val=tuple(sides["val"]), test=tuple(sides["test"]))


def tiled(
    job: TrainingJob, spec: HeadTypeSpec, usable: list[TrainingSample]
) -> list[TrainingSample]:
    tiles = job.config.tile_long_edge
    if tiles <= 1 or spec.task != "detection":
        return usable
    result = tile_samples(usable, tiles, seed=job.config.split_seed)
    job.notes.append(
        f"Trained on tiles, {tiles} along the long side: {len(usable)} pictures became "
        f"{len(result)} tiles."
    )
    return result


Evaluation = tuple[float, list[dict[str, Tensor]], list[dict[str, Tensor]]]


def evaluator(
    live: LivePass | None, head: nn.Module, compute_loss: LossFn, cache: list[CachedSample]
) -> Callable[[tuple[int, ...]], Evaluation]:
    """Validation or test over some indices, through whichever pass the run uses."""

    def run(indices: tuple[int, ...]) -> Evaluation:
        if live is None:
            return evaluate(head, compute_loss, cache, indices)
        return evaluate_live(live, head, compute_loss, indices)

    return run


NO_TEST_OBJECTS_NOTE = (
    "The test pictures hold no annotated objects, so there is no test score: 0 would "
    "wrongly read as 'finds nothing'. Split again with more scenes, or add pictures."
)


def _has_objects(targets: list[dict[str, Tensor]]) -> bool:
    """False only when every target is a detection target with no positive cell."""
    for target in targets:
        positive = target.get("positive")
        if positive is None or bool(positive.any()):
            return True
    return False


def score_test(
    job: TrainingJob,
    head: nn.Module,
    run: Callable[[], Evaluation],
    decode: Callable[[dict[str, Tensor], int], dict[str, Tensor]],
    compute_metrics: Callable[[list[dict[str, Tensor]], list[dict[str, Tensor]]], dict[str, float]],
    patch_size: int,
) -> None:
    """The best weights, scored once on pictures neither training nor selection saw."""
    if job.best_state is None:
        return
    head.load_state_dict(job.best_state)
    _, outputs, targets = run()
    if not _has_objects(targets):
        job.notes.append(NO_TEST_OBJECTS_NOTE)
        return
    decoded = [decode(out, patch_size) for out in outputs]
    job.test_metrics = compute_metrics(decoded, targets) if decoded else {}


__all__ = [
    "Prepared",
    "choose_split",
    "evaluator",
    "prepare",
    "preset_name",
    "score_test",
    "tiled",
]
