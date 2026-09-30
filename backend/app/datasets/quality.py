"""Annotation quality aids (doc 109): a written guideline, and a second look at a sample.

Both are files beside the dataset, like its recipes: they describe the annotation work,
not any one annotation, and survive a re-save of every picture.
"""

from __future__ import annotations

import json
import logging
import random
from typing import Literal

from pydantic import BaseModel

from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.store import dataset_dir

logger = logging.getLogger(__name__)

GUIDELINE_FILE = "guideline.md"
SECOND_LOOK_FILE = "second_look.json"
MAX_GUIDELINE = 20_000
MIN_SAMPLE = 5

Verdict = Literal["right", "changed"]


class SecondLook(BaseModel):
    sample: list[str]
    #: path → "right" | "changed"
    verdicts: dict[str, Verdict] = {}

    @property
    def reviewed(self) -> int:
        return sum(1 for path in self.sample if path in self.verdicts)

    @property
    def changed(self) -> int:
        return sum(1 for path in self.sample if self.verdicts.get(path) == "changed")


def read_guideline(dataset_id: str, settings: Settings | None = None) -> str:
    path = dataset_dir(dataset_id, settings) / GUIDELINE_FILE
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def write_guideline(dataset_id: str, text: str, settings: Settings | None = None) -> str:
    if len(text) > MAX_GUIDELINE:
        raise ValueError(f"A guideline is at most {MAX_GUIDELINE} characters.")
    directory = dataset_dir(dataset_id, settings)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / GUIDELINE_FILE).write_text(text, encoding="utf-8")
    return text


def _annotated(dataset_id: str, settings: Settings | None) -> list[str]:
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT i.path FROM images i WHERE i.dataset_id = ? AND COALESCE(i.excluded, 0) = 0"
            " AND (EXISTS (SELECT 1 FROM boxes b WHERE b.image_id = i.id)"
            "   OR EXISTS (SELECT 1 FROM masks m WHERE m.image_id = i.id)) ORDER BY i.id",
            (dataset_id,),
        ).fetchall()
    return [str(row["path"]) for row in rows]


def draw_sample(
    dataset_id: str, share: float, seed: int, settings: Settings | None = None
) -> SecondLook:
    """A new random sample of the annotated pictures: `share` of them, at least five."""
    if not 0 < share <= 1:
        raise ValueError("The share must be above 0 and at most 1.")
    annotated = _annotated(dataset_id, settings)
    if not annotated:
        raise ValueError("Nothing is annotated yet, so there is nothing to look at twice.")
    size = min(len(annotated), max(MIN_SAMPLE, round(len(annotated) * share)))
    look = SecondLook(sample=sorted(random.Random(seed).sample(annotated, size)))
    _save(dataset_id, look, settings)
    return look


def load_second_look(dataset_id: str, settings: Settings | None = None) -> SecondLook | None:
    path = dataset_dir(dataset_id, settings) / SECOND_LOOK_FILE
    if not path.is_file():
        return None
    try:
        return SecondLook.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except ValueError as error:
        logger.warning("Ignoring an unreadable %s: %s", path, error)
        return None


def record_verdict(
    dataset_id: str, path: str, verdict: Verdict, settings: Settings | None = None
) -> SecondLook:
    look = load_second_look(dataset_id, settings)
    if look is None:
        raise LookupError("No second look has been started for this dataset.")
    if path not in look.sample:
        raise ValueError("That picture is not in the second-look sample.")
    look.verdicts[path] = verdict
    _save(dataset_id, look, settings)
    return look


def _save(dataset_id: str, look: SecondLook, settings: Settings | None) -> None:
    directory = dataset_dir(dataset_id, settings)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / SECOND_LOOK_FILE).write_text(look.model_dump_json(indent=2), encoding="utf-8")


__all__ = [
    "SecondLook",
    "draw_sample",
    "load_second_look",
    "read_guideline",
    "record_verdict",
    "write_guideline",
]
