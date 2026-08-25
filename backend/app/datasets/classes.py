"""A dataset's class vocabulary (doc 60).

Until this module existed, a class in this project was `boxes.prompt` — a string on an
annotation. That has one consequence the Annotation Studio could not work around: a class
could not exist before a box carried it, so "create a new class, then choose it" was
literally unrepresentable. `dataset_classes` is the missing half.

**The vocabulary is the union of two sources, and both are load-bearing.** The table holds
classes someone created; `boxes.prompt` holds classes that arrived with a proposal run or a
COCO import. A dataset annotated before this feature existed has thirteen classes and zero
rows — reading only the table would open the picker empty on a dataset visibly full of
named boxes.

Its own module rather than a section of `store.py`, which is at 284 lines against the
project's 300-line gate. The seam is real: everything here is about names, and nothing here
reads or writes an annotation.
"""

from __future__ import annotations

import logging
import sqlite3

from pydantic import BaseModel

from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.images import now as _now

logger = logging.getLogger(__name__)

#: Long enough for any real class name and short enough that a caller cannot store an
#: unbounded string. Enforced at the API layer too, where it becomes a 422.
MAX_CLASS_NAME = 100


class ClassInfo(BaseModel):
    """One class as the picker shows it."""

    name: str
    #: How many annotations currently carry it. Zero means "created, not yet used" —
    #: a real state, and one the UI should be able to tell apart from an error.
    boxes: int
    #: True when it is in `dataset_classes`. False means it was inferred from a box, which
    #: is what every class in a pre-doc-60 dataset looks like.
    stored: bool


def normalise(name: str) -> str:
    """Trim, and reject what cannot be a class.

    Raises `ValueError` so the API layer's `ValueError → 422` backstop catches it without
    this module knowing about HTTP.
    """
    trimmed = name.strip()
    if not trimmed:
        raise ValueError("A class name cannot be empty.")
    if len(trimmed) > MAX_CLASS_NAME:
        raise ValueError(f"A class name cannot exceed {MAX_CLASS_NAME} characters.")
    return trimmed


class ClassStore:
    """Reads and writes for the class vocabulary. Instantiated per request; holds no state."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    def list_for(self, dataset_id: str) -> list[ClassInfo]:
        """The dataset's vocabulary — stored ∪ in-use — sorted case-insensitively.

        One query per source rather than a SQL UNION, because the two carry different
        information: the table says a class exists, the boxes say how many carry it. A
        UNION would flatten exactly the distinction the picker needs.
        """
        with transaction(self._settings) as connection:
            stored = [
                str(row["name"])
                for row in connection.execute(
                    "SELECT name FROM dataset_classes WHERE dataset_id = ?", (dataset_id,)
                )
            ]
            counts = _box_counts(connection, dataset_id)

        # Case-insensitive keys, first spelling wins — the same rule `create` enforces,
        # so a stored `Pedestrian` and a box's `pedestrian` are one entry, not two.
        merged: dict[str, ClassInfo] = {}
        for name in stored:
            merged[name.casefold()] = ClassInfo(name=name, boxes=0, stored=True)
        for name, count in counts.items():
            key = name.casefold()
            existing = merged.get(key)
            if existing is None:
                merged[key] = ClassInfo(name=name, boxes=count, stored=False)
            else:
                merged[key] = ClassInfo(
                    name=existing.name, boxes=existing.boxes + count, stored=existing.stored
                )

        return sorted(merged.values(), key=lambda entry: entry.name.casefold())

    def create(self, dataset_id: str, name: str) -> bool:
        """Add a class. Returns True when it was new.

        **Idempotent by decision.** Two reviewers creating `pedestrian` is not an error, and
        a 409 would make the caller handle a case whose correct resolution is "you already
        have it". A name already carried by a box but absent from the table *is* inserted —
        that promotes an inferred class to a stored one, which is what makes it survive the
        last box carrying it being deleted.
        """
        clean = normalise(name)
        with transaction(self._settings) as connection:
            existing = connection.execute(
                "SELECT name FROM dataset_classes WHERE dataset_id = ? AND name = ? COLLATE NOCASE",
                (dataset_id, clean),
            ).fetchone()
            if existing is not None:
                return False
            connection.execute(
                "INSERT INTO dataset_classes (dataset_id, name, created_at) VALUES (?, ?, ?)",
                (dataset_id, clean, _now()),
            )
        logger.info("Added class %r to dataset %s", clean, dataset_id)
        return True

    def delete(self, dataset_id: str, name: str) -> bool:
        """Remove a class from the vocabulary. Returns True when a row was removed.

        **Never touches a box.** Deleting a class that forty annotations carry would either
        orphan them or silently rewrite forty annotations, and a picker's delete affordance
        must not be able to do either. A name still on a box therefore keeps appearing in
        `list_for` as `stored: False`, which is the honest answer rather than a lie of
        omission.
        """
        with transaction(self._settings) as connection:
            cursor = connection.execute(
                "DELETE FROM dataset_classes WHERE dataset_id = ? AND name = ? COLLATE NOCASE",
                (dataset_id, name.strip()),
            )
            removed = cursor.rowcount > 0
        if removed:
            logger.info("Removed class %r from dataset %s", name, dataset_id)
        return removed


def _box_counts(connection: sqlite3.Connection, dataset_id: str) -> dict[str, int]:
    """Distinct non-empty `boxes.prompt` in a dataset, with how many carry each.

    `prompt` is nullable and Wave 1 wrote empty strings for an unnamed box, so both are
    excluded — neither is a class, and offering `''` in a picker that already has an
    explicit "unnamed" option would be two ways to say the same thing.
    """
    rows = connection.execute(
        "SELECT b.prompt AS name, COUNT(*) AS n"
        " FROM boxes b JOIN images i ON b.image_id = i.id"
        " WHERE i.dataset_id = ? AND b.prompt IS NOT NULL AND TRIM(b.prompt) != ''"
        " GROUP BY b.prompt",
        (dataset_id,),
    ).fetchall()
    return {str(row["name"]): int(row["n"]) for row in rows}


__all__ = ["MAX_CLASS_NAME", "ClassInfo", "ClassStore", "normalise"]
