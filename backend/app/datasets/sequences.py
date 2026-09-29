"""Datasets as sequences: which images are frames of which video or folder (doc 73).

The Generator records a frame's position when it saves it; this reads it back. Kept apart
from ``store.py`` because every question here is about order in time, which nothing else
in the store has ever needed to ask.
"""

from __future__ import annotations

from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.models import FramePosition


def image_frames(dataset_id: str, settings: Settings | None = None) -> dict[str, FramePosition]:
    """Where each image sits in its sequence, for the images that are frames."""
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT path, sequence, frame_index FROM images"
            " WHERE dataset_id = ? AND sequence IS NOT NULL AND frame_index IS NOT NULL",
            (dataset_id,),
        ).fetchall()
    return {
        str(row["path"]): FramePosition(
            sequence=str(row["sequence"]), frame_index=int(row["frame_index"])
        )
        for row in rows
    }


__all__ = ["image_frames"]
