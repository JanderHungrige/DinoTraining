"""A dataset's preparation state: how training should read its classes (doc 83).

Kept apart from ``fixes.py`` so that the audit, which must describe the dataset as training
will see it, can read the state without depending on the fixes that write it.
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.datasets.store import dataset_dir

logger = logging.getLogger(__name__)

STATE_FILE = "prep_state.json"


class PrepState(BaseModel):
    #: Class as written (normalised) -> class to train it as, or None to leave it out.
    class_map: dict[str, str | None] = Field(default_factory=dict)


def load_state(dataset_id: str, settings: Settings | None = None) -> PrepState:
    path = dataset_dir(dataset_id, settings) / STATE_FILE
    if not path.is_file():
        return PrepState()
    try:
        return PrepState.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except ValueError as error:
        logger.warning("Ignoring an unreadable %s: %s", path, error)
        return PrepState()


def save_state(dataset_id: str, state: PrepState, settings: Settings | None = None) -> None:
    directory = dataset_dir(dataset_id, settings)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / STATE_FILE).write_text(state.model_dump_json(indent=2), encoding="utf-8")


__all__ = ["PrepState", "load_state", "save_state"]
