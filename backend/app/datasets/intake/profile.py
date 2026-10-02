"""A dataset's parameters, computed live from the store so they never go stale (doc 136).

Jan's list: when it was created, images or video, how many pictures, with or without
annotations, how many annotated, how many classes, which kinds of annotation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from app.core.config import Settings
from app.datasets.classes import ClassStore
from app.datasets.db import transaction
from app.datasets.store import DatasetStore


def pending_paths(dataset_id: str, settings: Settings | None = None) -> set[str]:
    """Paths of the pictures imported without annotations and not saved since (doc 136)."""
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT path FROM images WHERE dataset_id = ? AND annotated_at = ''", (dataset_id,)
        ).fetchall()
    return {str(row["path"]) for row in rows}


Media = Literal["images", "video", "mixed", "empty"]


class DatasetProfile(BaseModel):
    dataset_id: str
    name: str
    created_at: str
    description: str | None
    source: str | None
    media: Media
    pictures: int
    annotated_pictures: int
    sequences: int
    classes: list[str]
    annotation_types: list[str]
    #: Doc 143: the last export, for the list ("exported 3 min ago").
    exported_at: str | None = None
    exported_folder: str | None = None
    #: Doc 149: a linked dataset's bucket, and how many of its pictures are cached.
    linked: str | None = None
    cached: int | None = None


def dataset_profile(dataset_id: str, settings: Settings | None = None) -> DatasetProfile:
    info = DatasetStore(settings).get(dataset_id)
    with transaction(settings) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS pictures,"
            " SUM(annotated_at != '') AS annotated,"
            " SUM(sequence IS NOT NULL) AS framed,"
            " COUNT(DISTINCT sequence) AS sequences"
            " FROM images WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()
        has_boxes = connection.execute(
            "SELECT 1 FROM boxes JOIN images ON images.id = boxes.image_id"
            " WHERE images.dataset_id = ? LIMIT 1",
            (dataset_id,),
        ).fetchone()
        has_masks = connection.execute(
            "SELECT 1 FROM masks JOIN images ON images.id = masks.image_id"
            " WHERE images.dataset_id = ? LIMIT 1",
            (dataset_id,),
        ).fetchone()
    pictures = int(row["pictures"] or 0)
    framed = int(row["framed"] or 0)
    media: Media = (
        "empty"
        if pictures == 0
        else "video"
        if framed == pictures
        else "mixed"
        if framed
        else "images"
    )
    types = [kind for kind, found in (("boxes", has_boxes), ("masks", has_masks)) if found]
    exported_at, exported_folder = _exported(dataset_id, settings)
    return DatasetProfile(
        dataset_id=dataset_id,
        name=info.name,
        created_at=info.created_at,
        description=info.description,
        source=info.source,
        media=media,
        pictures=pictures,
        annotated_pictures=int(row["annotated"] or 0),
        sequences=int(row["sequences"] or 0),
        classes=sorted(entry.name for entry in ClassStore(settings).list_for(dataset_id)),
        annotation_types=types,
        exported_at=exported_at,
        exported_folder=exported_folder,
        **_linked(dataset_id, settings),
    )


def _exported(dataset_id: str, settings: Settings | None) -> tuple[str | None, str | None]:
    """Doc 143's last export. Imported here, not at the top: the exchange package reads
    this module's `pending_paths`."""
    from app.datasets.exchange.targets import exported_summary

    return exported_summary(dataset_id, settings)


def _linked(dataset_id: str, settings: Settings | None) -> dict[str, Any]:
    """Doc 149: for a linked dataset, its bucket and its cached pictures (what works offline)."""
    from app.cloud.links import all_links

    link = next((entry for entry in all_links(settings) if entry.dataset_id == dataset_id), None)
    if link is None:
        return {}
    with transaction(settings) as connection:
        rows = connection.execute("SELECT path FROM images WHERE dataset_id = ?", (dataset_id,))
        paths = [row["path"] for row in rows]
    return {"linked": link.uri, "cached": sum(1 for path in paths if Path(path).is_file())}
