"""The samples a fine-tune trains and is judged on (doc 93).

Read through `build_samples`, so exclusions and the class map apply (doc 90). With a
recipe the stored split is used: that is what makes "fine-tuned beats base" a claim about
pictures the model never saw rather than about neighbouring frames. Without one, a seeded
random split, and the job notes it.
"""

from __future__ import annotations

import random

from app.core.config import Settings
from app.datasets.masks import MaskStore
from app.datasets.store import DatasetStore
from app.finetune.adapter import FinetuneData
from app.finetune.requirements import FinetuneRequirements
from app.ml.training.samples import TrainingSample, build_samples


def _usable(samples: list[TrainingSample], spec: FinetuneRequirements) -> list[TrainingSample]:
    if spec.annotation_kind == "boxes":
        return [s for s in samples if s.targets]
    if spec.annotation_kind == "image-labels":
        return [s for s in samples if s.image_class is not None]
    return [s for s in samples if s.segmented]


def load_data(
    spec: FinetuneRequirements,
    dataset_ids: tuple[str, ...],
    recipe_id: str | None,
    seed: int,
    settings: Settings | None = None,
) -> FinetuneData:
    sample_set = build_samples(DatasetStore(settings), dataset_ids, MaskStore(settings))
    names = (
        sample_set.mask_class_names
        if spec.annotation_kind in ("instance-masks", "phrase-masks")
        else sample_set.class_names
    )
    usable = _usable(sample_set.samples, spec)
    if recipe_id is not None:
        sides = {side: [s for s in usable if s.split == side] for side in ("train", "val", "test")}
        return FinetuneData(sides["train"], sides["val"], sides["test"], names)
    shuffled = usable[:]
    random.Random(seed).shuffle(shuffled)
    held = max(1, len(shuffled) // 5)
    return FinetuneData(shuffled[held:], shuffled[:held], [], names)


__all__ = ["load_data"]
