"""What the Prepare steps decided, applied to the samples training reads (docs 83, 84, 90).

Two of those decisions apply to **every** run, recipe or not, because the user made them
explicitly in the Fix step and was told training would honour them:

* **excluded images** are left out;
* **the class map** renames and merges classes, and a class *left out* has its boxes and
  masks turned into ignore regions (`unclear`). Turning them into background instead
  would teach the model that those objects are background, which is the opposite of
  "leave this class out of this run".

The stored split is read here too, and used only by a run that names a recipe; without
one the runner keeps its random split and says the data is unprepared.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TypeVar

from app.core.config import Settings
from app.datasets.class_names import normalise_class_name
from app.datasets.db import transaction
from app.datasets.images import NEVER_SAVED
from app.datasets.models import Box, Mask
from app.prep.state import load_state

Annotation = TypeVar("Annotation", Box, Mask)


@dataclass(frozen=True)
class Preparation:
    excluded: frozenset[int] = frozenset()
    #: image id → "train", "val", "test" or "buffer".
    split: dict[int, str] = field(default_factory=dict)
    class_map: dict[str, str | None] = field(default_factory=dict)


def load_preparation(dataset_id: str, settings: Settings | None = None) -> Preparation:
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT id, COALESCE(excluded, 0) AS excluded, split, annotated_at"
            " FROM images WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchall()
    return Preparation(
        # Doc 136: a picture nobody has annotated yet is not background; leave it out.
        excluded=frozenset(
            int(r["id"]) for r in rows if r["excluded"] or r["annotated_at"] == NEVER_SAVED
        ),
        split={int(r["id"]): str(r["split"]) for r in rows if r["split"]},
        class_map=load_state(dataset_id, settings).class_map,
    )


def mapped(annotation: Annotation, class_map: dict[str, str | None]) -> Annotation:
    """The annotation as training reads it under the class map."""
    name = normalise_class_name(annotation.prompt)
    if name not in class_map:
        return annotation
    target = class_map[name]
    if target is None:
        # Left out: not a target, and not background either.
        return annotation.model_copy(update={"label": "unclear"})
    return annotation.model_copy(update={"prompt": target})


def prepared_rows(
    rows: Sequence[tuple[int, str, int, int, list[Annotation]]], prep: Preparation
) -> list[tuple[int, str, int, int, list[Annotation]]]:
    """Rows of (image id, path, width, height, annotations), prepared."""
    return [
        (image_id, path, width, height, [mapped(a, prep.class_map) for a in annotations])
        for image_id, path, width, height, annotations in rows
        if image_id not in prep.excluded
    ]


__all__ = ["Preparation", "load_preparation", "mapped", "prepared_rows"]
