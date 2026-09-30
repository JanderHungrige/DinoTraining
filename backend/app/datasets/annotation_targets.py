"""What a dataset is annotated for, and what that asks of each picture (doc 104).

One matrix, read by the Studio and by MCP: the same words tell a person and an assistant
which layers a model needs and why the others are still worth having.
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from pydantic import BaseModel

from app.core.config import Settings
from app.datasets.store import dataset_dir

logger = logging.getLogger(__name__)

Level = Literal["required", "recommended", "optional"]
TARGET_FILE = "annotation_target.json"
DEFAULT_TARGET = "open"


class LayerRule(BaseModel):
    layer: str
    label: str
    level: Level
    why: str


class AnnotationTarget(BaseModel):
    id: str
    label: str
    #: One line: what choosing it asks of you.
    summary: str
    #: The Prepare data profile it trains (doc 101), or None for "open".
    profile: str | None
    layers: list[LayerRule]


LABELS = {
    "picture-class": "One class per picture",
    "boxes": "Boxes",
    "masks": "Outlines (masks)",
    "phrases": "Phrases",
    "picture-status": "Complete when saved",
}


def _t(
    tid: str, label: str, summary: str, profile: str | None, rules: dict[str, tuple[Level, str]]
) -> AnnotationTarget:
    return AnnotationTarget(
        id=tid,
        label=label,
        summary=summary,
        profile=profile,
        layers=[
            LayerRule(layer=k, label=LABELS[k], level=v[0], why=v[1]) for k, v in rules.items()
        ],
    )


_CLASS_FROM_BOXES = (
    "A classifier takes a picture's class from its annotations; a picture "
    "with two classes is skipped."
)
_MASKS_LATER = (
    "Outlines keep this dataset usable for SAM 2 and SAM 3 later — one click from your boxes."
)
_PHRASES_LATER = "Only SAM 3 reads phrases; the class name already is one."
_STATUS_LATER = "Only SAM 3 uses it: which pictures are complete for which class."

TARGETS: tuple[AnnotationTarget, ...] = (
    _t(
        "open",
        "Keep all options open",
        "Boxes, outlines and phrases — any model can train on it later. Recommended.",
        None,
        {
            "picture-class": ("optional", _CLASS_FROM_BOXES),
            "boxes": ("recommended", "Every model starts from knowing where the objects are."),
            "masks": (
                "recommended",
                "SAM 2 and SAM 3 need outlines; they come from your boxes in one click.",
            ),
            "phrases": (
                "recommended",
                (
                    "The class name is already a phrase; 2–4 variations help SAM 3 "
                    "understand other wordings."
                ),
            ),
            "picture-status": (
                "recommended",
                (
                    "A saved picture counts as complete for the classes that exist then; "
                    "SAM 3 learns 'not here' from it. Pictures saved before a class was "
                    "added are reviewed for it."
                ),
            ),
        },
    ),
    _t(
        "classifier",
        "Picture classifier",
        "One class per picture.",
        "head-classification-dinov2",
        {
            "picture-class": (
                "required",
                (
                    "Every picture's annotations name one class — mark the main object; a "
                    "picture with two is skipped."
                ),
            ),
            "boxes": (
                "optional",
                (
                    "One box on the main object is enough to name the picture; more boxes "
                    "keep it useful for a detector."
                ),
            ),
            "masks": ("optional", _MASKS_LATER),
            "phrases": ("optional", _PHRASES_LATER),
            "picture-status": ("optional", _STATUS_LATER),
        },
    ),
    _t(
        "detector",
        "Detector (boxes)",
        "A tight box around every object.",
        "rf-detr-nano",
        {
            "picture-class": ("optional", _CLASS_FROM_BOXES),
            "boxes": (
                "required",
                (
                    "One tight box around every object of every class you train — a missed "
                    "object is taught as background."
                ),
            ),
            "masks": ("optional", _MASKS_LATER),
            "phrases": ("optional", _PHRASES_LATER),
            "picture-status": ("optional", _STATUS_LATER),
        },
    ),
    _t(
        "sam2",
        "Instance outlines (SAM 2)",
        "One outline per object, in your convention.",
        "sam2.1-hiera-small",
        {
            "picture-class": ("optional", _CLASS_FROM_BOXES),
            "boxes": ("optional", "Each outline's box is derived from it; nothing extra to draw."),
            "masks": (
                "required",
                (
                    "One outline per object, drawn the way you want SAM to draw it: what "
                    "counts as part of the object."
                ),
            ),
            "phrases": ("optional", _PHRASES_LATER),
            "picture-status": ("optional", _STATUS_LATER),
        },
    ),
    _t(
        "sam3",
        "Concept outlines (SAM 3)",
        "Every instance of each phrase outlined, and each picture checked.",
        "sam3",
        {
            "picture-class": ("optional", _CLASS_FROM_BOXES),
            "boxes": ("optional", "Each outline's box is derived from it; nothing extra to draw."),
            "masks": (
                "required",
                (
                    "Every instance of a phrase in the picture is outlined — one left out "
                    "is taught as 'not this'."
                ),
            ),
            "phrases": (
                "required",
                (
                    "What you would type to find it: the class name plus 2–4 variations. "
                    "More synonyms are not needed."
                ),
            ),
            "picture-status": (
                "required",
                (
                    "Mark each picture 'all marked' or 'not in this picture' per phrase: an "
                    "unchecked picture teaches nothing, a checked empty one teaches 'not "
                    "here'."
                ),
            ),
        },
    ),
)

_BY_ID = {target.id: target for target in TARGETS}


def get_target(target_id: str) -> AnnotationTarget:
    if target_id not in _BY_ID:
        raise ValueError(f"Unknown annotation target: {target_id}. Known: {', '.join(_BY_ID)}")
    return _BY_ID[target_id]


def load_target(dataset_id: str, settings: Settings | None = None) -> str:
    path = dataset_dir(dataset_id, settings) / TARGET_FILE
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))["target"]
    except FileNotFoundError:
        return DEFAULT_TARGET
    except (OSError, ValueError, KeyError, TypeError) as error:
        logger.warning("Ignoring an unreadable %s: %s", path, error)
        return DEFAULT_TARGET
    return str(stored) if stored in _BY_ID else DEFAULT_TARGET


def save_target(dataset_id: str, target_id: str, settings: Settings | None = None) -> str:
    get_target(target_id)
    directory = dataset_dir(dataset_id, settings)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / TARGET_FILE).write_text(json.dumps({"target": target_id}), encoding="utf-8")
    return target_id


__all__ = ["TARGETS", "AnnotationTarget", "LayerRule", "get_target", "load_target", "save_target"]
