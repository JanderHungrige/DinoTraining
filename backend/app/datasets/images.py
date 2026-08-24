"""Getting one image into a dataset — the file on disk and the row in SQLite.

Split out of ``store.py`` when the mask write path arrived: both the box and the mask paths
need exactly this and nothing else of the store's, and duplicating it would let the two
disagree about when a second row is created for the same picture.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.core.paths import ensure_within

logger = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def upsert_image(
    connection: sqlite3.Connection,
    dataset_id: str,
    stored_path: str,
    width: int,
    height: int,
) -> int:
    """Insert or refresh one image row and return its id.

    Shared by the box and mask write paths, so saving masks for an image the user already
    boxed reuses the same row rather than creating a second one — ``UNIQUE (dataset_id,
    path)`` is what makes both paths agree.
    """
    connection.execute(
        "INSERT INTO images (dataset_id, path, width, height, annotated_at)"
        " VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(dataset_id, path) DO UPDATE SET"
        "   width = excluded.width,"
        "   height = excluded.height,"
        "   annotated_at = excluded.annotated_at",
        (dataset_id, stored_path, width, height, now()),
    )
    row = connection.execute(
        "SELECT id FROM images WHERE dataset_id = ? AND path = ?",
        (dataset_id, stored_path),
    ).fetchone()
    return int(row["id"])


def store_image_file(
    dataset_dir: Path,
    connection: sqlite3.Connection,
    dataset_id: str,
    source_path: str,
) -> str:
    """Copy the image into the dataset when ``copy_images`` is on; else keep the path."""
    row = connection.execute(
        "SELECT copy_images FROM datasets WHERE id = ?", (dataset_id,)
    ).fetchone()
    if row is None or not row["copy_images"]:
        return source_path

    source = Path(source_path)
    if not source.is_file():
        # Reference it anyway: a missing source is the caller's problem to report, and
        # failing the whole save would lose the labels the user just made.
        logger.warning("Cannot copy missing image %s", source_path)
        return source_path

    images_dir = dataset_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    destination = ensure_within(images_dir, images_dir / source.name)
    if not destination.exists():
        shutil.copy2(source, destination)
    return str(destination)
