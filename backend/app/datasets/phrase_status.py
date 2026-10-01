"""Whether a picture was checked for a phrase (doc 103).

Its own write, never part of saving the masks: re-saving an image's masks must not clear
"I checked this for *signal*".
"""

from __future__ import annotations

import sqlite3

from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.phrase_links import ensure_phrase, phrase_key
from app.datasets.phrases import PictureStatus, Status


def _image_id(connection: sqlite3.Connection, dataset_id: str, path: str) -> int:
    row = connection.execute(
        "SELECT id FROM images WHERE dataset_id = ? AND path = ?", (dataset_id, path)
    ).fetchone()
    if row is None:
        raise LookupError(f"No such picture in this dataset: {path}")
    return int(row["id"])


def _class_for(connection: sqlite3.Connection, dataset_id: str, key: str) -> str:
    """The class a phrase text belongs to: its row's, or the class it is the name of."""
    row = connection.execute(
        "SELECT class_name FROM phrases WHERE dataset_id = ? AND text = ?", (dataset_id, key)
    ).fetchone()
    if row is not None:
        return str(row["class_name"])
    for query in (
        "SELECT DISTINCT m.prompt AS name FROM masks m JOIN images i ON m.image_id = i.id"
        " WHERE i.dataset_id = ?",
        "SELECT name FROM dataset_classes WHERE dataset_id = ?",
    ):
        for found in connection.execute(query, (dataset_id,)):
            if phrase_key(found["name"] or "") == key:
                return str(found["name"])
    raise ValueError(f"Unknown phrase '{key}': add it first.")


def statuses_for(
    dataset_id: str, path: str, settings: Settings | None = None
) -> list[PictureStatus]:
    with transaction(settings) as connection:
        image_id = _image_id(connection, dataset_id, path)
        rows = connection.execute(
            "SELECT s.phrase_id, p.text, s.status FROM image_phrase_status s"
            " JOIN phrases p ON p.id = s.phrase_id WHERE s.image_id = ? ORDER BY p.text",
            (image_id,),
        ).fetchall()
    return [
        PictureStatus(phrase_id=r["phrase_id"], text=r["text"], status=r["status"]) for r in rows
    ]


def set_status(
    dataset_id: str,
    path: str,
    phrase: str,
    status: Status | None,
    settings: Settings | None = None,
) -> list[PictureStatus]:
    """Mark a picture checked for a phrase, or clear it (None). Returns its statuses."""
    key = phrase_key(phrase)
    with transaction(settings) as connection:
        image_id = _image_id(connection, dataset_id, path)
        phrase_id = ensure_phrase(
            connection, dataset_id, key, _class_for(connection, dataset_id, key)
        )
        if status is None:
            connection.execute(
                "DELETE FROM image_phrase_status WHERE image_id = ? AND phrase_id = ?",
                (image_id, phrase_id),
            )
        else:
            connection.execute(
                "INSERT INTO image_phrase_status (image_id, phrase_id, status) VALUES (?, ?, ?)"
                " ON CONFLICT(image_id, phrase_id) DO UPDATE SET status = excluded.status",
                (image_id, phrase_id, status),
            )
    return statuses_for(dataset_id, path, settings)


def fill_unchecked(
    dataset_id: str, phrase: str, settings: Settings | None = None
) -> dict[str, int]:
    """'This phrase is fully annotated': every picture not yet checked for it is marked —
    `complete` where an accepted outline answers to it, `absent` where none does.

    One step instead of a click per picture, for a dataset that is already exhaustively
    annotated (an imported COCO set, or one finished by hand). Checks already set stay.
    """
    key = phrase_key(phrase)
    with transaction(settings) as connection:
        phrase_id = ensure_phrase(
            connection, dataset_id, key, _class_for(connection, dataset_id, key)
        )
        unchecked = [
            int(r["id"])
            for r in connection.execute(
                "SELECT i.id FROM images i WHERE i.dataset_id = ? AND COALESCE(i.excluded, 0) = 0"
                " AND NOT EXISTS (SELECT 1 FROM image_phrase_status s"
                "   WHERE s.image_id = i.id AND s.phrase_id = ?)",
                (dataset_id, phrase_id),
            )
        ]
        # An outline answers when its class *is* the phrase (the same key everywhere) or
        # when it is linked to it.
        answering = {
            int(r["image_id"])
            for r in connection.execute(
                "SELECT m.image_id, m.prompt,"
                " EXISTS (SELECT 1 FROM mask_phrases mp WHERE mp.mask_id = m.id"
                "   AND mp.phrase_id = ?) AS linked"
                " FROM masks m JOIN images i ON i.id = m.image_id"
                " WHERE i.dataset_id = ? AND m.label = 'positive'",
                (phrase_id, dataset_id),
            )
            if r["linked"] or phrase_key(r["prompt"] or "") == key
        }
        marks = [(i, phrase_id, "complete" if i in answering else "absent") for i in unchecked]
        connection.executemany(
            "INSERT INTO image_phrase_status (image_id, phrase_id, status) VALUES (?, ?, ?)", marks
        )
    return {
        "complete": sum(1 for *_, status in marks if status == "complete"),
        "absent": sum(1 for *_, status in marks if status == "absent"),
    }


__all__ = ["fill_unchecked", "set_status", "statuses_for"]
