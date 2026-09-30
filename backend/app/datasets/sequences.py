"""Datasets as sequences: which images are frames of which video or folder (docs 73–75).

The Generator records a frame's position when it saves it; this reads it back. Kept apart
from ``store.py`` because every question here is about order in time, which nothing else
in the store has ever needed to ask.

**A sequence is the whole source, not only the annotated frames.** Autoplay writes no
image where nothing was found (doc 70), so the database alone would play a video with its
empty stretches cut out, which is a different video. The frames that were decoded but never
saved are still on disk (a video's frames directory), or still in the folder, so they are
merged back in, unannotated, in the order the Generator numbered them.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.models import FramePosition
from app.ml.images import FolderNotFoundError, list_images
from app.ml.video.decode import looks_like_video
from app.ml.video.extract import frames_dir

logger = logging.getLogger(__name__)

_FRAME_FILE = re.compile(r"-f(\d{6})\.jpg$")


@dataclass
class SequenceFrame:
    index: int
    path: str
    #: True when the dataset holds this frame; false for a frame only on disk.
    annotated: bool = False
    #: Classes with a positive box or mask here, sorted. What the timeline is drawn from.
    classes: list[str] = field(default_factory=list)


@dataclass
class DatasetSequence:
    source: str
    kind: str
    frames: list[SequenceFrame]


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


def positive_classes(connection: sqlite3.Connection, dataset_id: str) -> dict[str, set[str]]:
    """Image path -> the classes it has a positive box or mask for."""
    rows = connection.execute(
        "SELECT i.path AS path, b.prompt AS prompt FROM images i"
        " JOIN boxes b ON b.image_id = i.id"
        " WHERE i.dataset_id = ? AND b.label = 'positive' AND b.prompt IS NOT NULL"
        " UNION"
        " SELECT i.path, m.prompt FROM images i"
        " JOIN masks m ON m.image_id = i.id"
        " WHERE i.dataset_id = ? AND m.label = 'positive' AND m.prompt IS NOT NULL",
        (dataset_id, dataset_id),
    ).fetchall()
    found: dict[str, set[str]] = {}
    for row in rows:
        found.setdefault(str(row["path"]), set()).add(str(row["prompt"]))
    return found


def _on_disk(source: str, dataset_dir: Path) -> dict[int, str]:
    """Every frame of the source that exists as a file, by the index the Generator used."""
    if looks_like_video(Path(source)):
        directory = frames_dir(dataset_dir, source)
        if not directory.is_dir():
            return {}
        return {
            int(match.group(1)): str(entry)
            for entry in directory.iterdir()
            if (match := _FRAME_FILE.search(entry.name))
        }
    try:
        # The same listing, and so the same order, the Generator numbered the folder by.
        return {index: str(path) for index, path in enumerate(list_images(source))}
    except FolderNotFoundError:
        # Moved or unmounted since: the annotated frames still play, from the dataset.
        logger.info("Sequence folder %s is gone; showing its annotated frames only", source)
        return {}


def dataset_sequences(
    dataset_id: str, dataset_dir: Path, settings: Settings | None = None
) -> tuple[list[DatasetSequence], list[SequenceFrame]]:
    """The dataset's sequences, each complete and in order, plus its loose images."""
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT path, sequence, frame_index FROM images WHERE dataset_id = ? ORDER BY id",
            (dataset_id,),
        ).fetchall()
        classes = positive_classes(connection, dataset_id)

    grouped: dict[str, dict[int, SequenceFrame]] = {}
    loose: list[SequenceFrame] = []
    for row in rows:
        path = str(row["path"])
        frame = SequenceFrame(
            index=int(row["frame_index"] if row["frame_index"] is not None else len(loose)),
            path=path,
            annotated=True,
            classes=sorted(classes.get(path, set())),
        )
        if row["sequence"] is None:
            loose.append(frame)
        else:
            grouped.setdefault(str(row["sequence"]), {})[frame.index] = frame

    sequences = []
    for source, annotated in grouped.items():
        frames = {
            index: SequenceFrame(index=index, path=path)
            for index, path in _on_disk(source, dataset_dir).items()
        }
        frames.update(annotated)
        kind = "video" if looks_like_video(Path(source)) else "folder"
        sequences.append(DatasetSequence(source, kind, [frames[i] for i in sorted(frames)]))
    return sequences, loose


__all__ = ["DatasetSequence", "SequenceFrame", "dataset_sequences", "image_frames"]
