"""Doc 145: each trained model exported to a folder when its training finishes.

Off unless `DINO_MODEL_EXPORT_FOLDER` names a folder. The export is doc 121's bundle,
written in a thread of its own so the next training does not wait; what it wrote, or why
it could not, goes into the job's notes and the log.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from app.core.config import Settings, get_settings
from app.ml.training.job import JOB_HOOKS, TrainingJob
from app.mlops.export import export_to

logger = logging.getLogger(__name__)

Note = Callable[[str], None]


def model_folder(settings: Settings | None = None) -> Path | None:
    folder = (settings or get_settings()).model_export_folder
    return Path(folder).expanduser() if folder else None


def export_after_training(
    kind: str, instance_id: str, note: Note, settings: Settings | None = None
) -> threading.Thread | None:
    """Start the export when the setting is on; returns the thread (tests wait on it)."""
    folder = model_folder(settings)
    if folder is None:
        return None

    def work() -> None:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            path = export_to(kind, instance_id, folder)
            note(f"Exported to {path}")
        except (LookupError, ValueError, OSError) as error:
            logger.warning("Automatic export of %s %s failed: %s", kind, instance_id, error)
            note(f"The automatic export to {folder} failed: {error}")

    thread = threading.Thread(target=work, name=f"model-export-{instance_id[:8]}", daemon=True)
    thread.start()
    return thread


def _attach(job: TrainingJob) -> None:
    if model_folder() is None:  # decided when the job starts: off means no listener at all
        return

    def listen(event: str, finished: TrainingJob) -> None:
        if event == "saved" and finished.head_instance_id:
            export_after_training("heads", finished.head_instance_id, finished.notes.append)

    job.listeners.append(listen)


def install() -> None:
    """Register the head-training hook once, at startup (as doc 123's tracking)."""
    if _attach not in JOB_HOOKS:
        JOB_HOOKS.append(_attach)
