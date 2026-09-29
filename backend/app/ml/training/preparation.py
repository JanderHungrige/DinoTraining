"""The prepared-data options a run applies: imbalance (doc 86) and augmentation (doc 87).

Gathered here so `runner._train` asks one question per epoch, "which cache indices, in
which order?", and does not grow a branch per option.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from app.ml.training.augmented import Variants, cache_variants, preset_for
from app.ml.training.imbalance import Balance, plan_balance

if TYPE_CHECKING:
    from app.ml.backbone import Backbone
    from app.ml.heads.registry import HeadTypeSpec
    from app.ml.preprocess import PreprocessPlan
    from app.ml.training.config import Split, TrainingConfig
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


__all__ = ["Prepared", "prepare", "preset_name"]
