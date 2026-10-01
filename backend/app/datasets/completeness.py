"""Saved means complete (doc 117): since when a class exists, and which saved pictures
were never looked at for it.

A picture is complete for every class that existed when it was last saved. The only gap
is a class added later: the pictures saved before it are *unknown* for it, and training
leaves them out for that class rather than reading them as "none here".
"""

from __future__ import annotations

import sqlite3

from app.datasets.phrase_links import ensure_phrase, phrase_key
from app.ml.concepts import prompt_terms


def class_since(connection: sqlite3.Connection, dataset_id: str) -> dict[str, str]:
    """Class key → the earliest moment it existed in this dataset (ISO timestamps)."""
    since: dict[str, str] = {}

    def earliest(name: str | None, moment: str | None) -> None:
        key = phrase_key(name or "")
        if key and moment and (key not in since or moment < since[key]):
            since[key] = moment

    for row in connection.execute(
        "SELECT name, created_at FROM dataset_classes WHERE dataset_id = ?", (dataset_id,)
    ):
        earliest(row["name"], row["created_at"])
    for table in ("masks", "boxes"):
        for row in connection.execute(
            f"SELECT a.prompt, MIN(i.annotated_at) AS first FROM {table} a"  # noqa: S608
            " JOIN images i ON i.id = a.image_id WHERE i.dataset_id = ? GROUP BY a.prompt",
            (dataset_id,),
        ):
            earliest(row["prompt"], row["first"])
    dataset = connection.execute(
        "SELECT prompt, created_at FROM datasets WHERE id = ?", (dataset_id,)
    ).fetchone()
    if dataset is not None and dataset["prompt"]:
        for term in prompt_terms(str(dataset["prompt"])):
            earliest(term, dataset["created_at"])
    return since


def saved_at(connection: sqlite3.Connection, dataset_id: str) -> dict[str, str]:
    """Picture path → when it was last saved."""
    return {
        str(row["path"]): str(row["annotated_at"])
        for row in connection.execute(
            "SELECT path, annotated_at FROM images WHERE dataset_id = ?", (dataset_id,)
        )
    }


def unknown_pictures(
    connection: sqlite3.Connection, dataset_id: str, class_name: str
) -> list[tuple[int, str]]:
    """(image id, path) of the saved pictures never looked at for `class_name`: saved
    before it existed, not excluded, and without an explicit check for it."""
    key = phrase_key(class_name)
    since = class_since(connection, dataset_id).get(key)
    if since is None:
        return []
    return [
        (int(row["id"]), str(row["path"]))
        for row in connection.execute(
            "SELECT i.id, i.path FROM images i WHERE i.dataset_id = ? AND i.annotated_at < ?"
            " AND COALESCE(i.excluded, 0) = 0 AND NOT EXISTS (SELECT 1 FROM image_phrase_status s"
            "   JOIN phrases p ON p.id = s.phrase_id WHERE s.image_id = i.id AND p.text = ?)"
            " ORDER BY i.path",
            (dataset_id, since, key),
        )
    ]


def completeness(connection: sqlite3.Connection, dataset_id: str) -> dict[str, dict[str, object]]:
    """Per class: `since` and how many saved pictures are `unknown` for it."""
    return {
        name: {"since": moment, "unknown": len(unknown_pictures(connection, dataset_id, name))}
        for name, moment in sorted(class_since(connection, dataset_id).items())
    }


def mark_absent(connection: sqlite3.Connection, dataset_id: str, class_name: str) -> int:
    """Doc 118, "it does not occur there": every picture unknown for the class is checked
    `absent` for it. Pictures already known or checked are left alone."""
    key = phrase_key(class_name)
    if key not in class_since(connection, dataset_id):
        raise ValueError(f"Not a class of this dataset: {key}.")
    pictures = unknown_pictures(connection, dataset_id, key)
    phrase_id = ensure_phrase(connection, dataset_id, key, key)
    connection.executemany(
        "INSERT OR IGNORE INTO image_phrase_status (image_id, phrase_id, status)"
        " VALUES (?, ?, 'absent')",
        [(image_id, phrase_id) for image_id, _ in pictures],
    )
    return len(pictures)


__all__ = ["class_since", "completeness", "mark_absent", "saved_at", "unknown_pictures"]
