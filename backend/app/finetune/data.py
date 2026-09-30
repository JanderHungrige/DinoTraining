"""The samples a fine-tune trains and is judged on (doc 93).

Read through `build_samples`, so exclusions and the class map apply (doc 90). With a
recipe the stored split is used: that is what makes "fine-tuned beats base" a claim about
pictures the model never saw rather than about neighbouring frames. Without one, a seeded
random split, and the job notes it.
"""

from __future__ import annotations

import random

from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.masks import MaskStore
from app.datasets.store import DatasetStore
from app.finetune.adapter import FinetuneData
from app.finetune.requirements import FinetuneRequirements
from app.ml.training.samples import TrainingSample, build_samples


def _checked_paths(dataset_ids: tuple[str, ...], settings: Settings | None) -> set[str]:
    """Pictures checked for a phrase (doc 108): a picture marked 'not in this picture' has
    no outline and is still a lesson."""
    with transaction(settings) as connection:
        return {
            str(row["path"])
            for dataset_id in dataset_ids
            for row in connection.execute(
                "SELECT DISTINCT i.path FROM image_phrase_status s JOIN images i"
                " ON i.id = s.image_id WHERE i.dataset_id = ?",
                (dataset_id,),
            )
        }


def _usable(
    samples: list[TrainingSample], spec: FinetuneRequirements, checked: set[str] | None = None
) -> list[TrainingSample]:
    if spec.annotation_kind == "phrase-masks":
        return [s for s in samples if s.segmented or s.path in (checked or set())]
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
    checked = (
        _checked_paths(dataset_ids, settings) if spec.annotation_kind == "phrase-masks" else set()
    )
    usable = _usable(sample_set.samples, spec, checked)
    if recipe_id is not None:
        sides = {side: [s for s in usable if s.split == side] for side in ("train", "val", "test")}
        return FinetuneData(sides["train"], sides["val"], sides["test"], names, dataset_ids)
    shuffled = usable[:]
    random.Random(seed).shuffle(shuffled)
    held = max(1, len(shuffled) // 5)
    return FinetuneData(shuffled[held:], shuffled[:held], [], names, dataset_ids)


__all__ = ["load_data"]
