"""Umbrella terms (doc 115): one phrase over several classes — "screw" for m8 and m9.

Connection-level, like `phrase_links`, so the phrase store can create an umbrella and its
members in one transaction.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from app.datasets.images import now
from app.datasets.phrase_links import phrase_key, variant_owner

#: An umbrella needs this many classes; with one it would be a variation.
MIN_MEMBERS = 2


def class_keys(connection: sqlite3.Connection, dataset_id: str) -> set[str]:
    """Every class of the dataset: stored, or carried by a mask or a box."""
    found: set[str] = set()
    for query in (
        "SELECT name FROM dataset_classes WHERE dataset_id = ?",
        "SELECT DISTINCT m.prompt AS name FROM masks m JOIN images i ON m.image_id = i.id"
        " WHERE i.dataset_id = ?",
        "SELECT DISTINCT b.prompt AS name FROM boxes b JOIN images i ON b.image_id = i.id"
        " WHERE i.dataset_id = ?",
    ):
        found.update(
            phrase_key(row["name"] or "") for row in connection.execute(query, (dataset_id,))
        )
    found.discard("")
    return found


def members_of(connection: sqlite3.Connection, dataset_id: str) -> dict[str, list[str]]:
    """Umbrella text → its member classes, sorted."""
    members: dict[str, list[str]] = {}
    for row in connection.execute(
        "SELECT p.text, pc.class_name FROM phrase_classes pc JOIN phrases p ON p.id = pc.phrase_id"
        " WHERE p.dataset_id = ? ORDER BY pc.class_name",
        (dataset_id,),
    ):
        members.setdefault(str(row["text"]), []).append(str(row["class_name"]))
    return members


def _checked_members(
    connection: sqlite3.Connection, dataset_id: str, text: str, classes: Iterable[str]
) -> list[str]:
    members = list(dict.fromkeys(k for c in classes if (k := phrase_key(c))))
    if len(members) < MIN_MEMBERS:
        raise ValueError(
            f"An umbrella term needs at least {MIN_MEMBERS} classes; for one class, add "
            f"'{text}' as a variation of it instead."
        )
    known = class_keys(connection, dataset_id)
    unknown = [m for m in members if m not in known]
    if unknown:
        raise ValueError(f"Not a class of this dataset: {', '.join(unknown)}.")
    return members


def add_umbrella(
    connection: sqlite3.Connection, dataset_id: str, text: str, classes: Iterable[str]
) -> int:
    """Create umbrella `text` over `classes`. The text must be new in every sense."""
    key = phrase_key(text)
    if key in class_keys(connection, dataset_id):
        raise ValueError(f"'{key}' is already a class; an umbrella term needs a name of its own.")
    if connection.execute(
        "SELECT 1 FROM phrases WHERE dataset_id = ? AND text = ?", (dataset_id, key)
    ).fetchone():
        raise ValueError(f"'{key}' is already a phrase of this dataset.")
    owner = variant_owner(connection, dataset_id, key)
    if owner is not None:
        raise ValueError(f"'{key}' is a variation of '{owner}'; use another name.")
    members = _checked_members(connection, dataset_id, key, classes)
    cursor = connection.execute(
        "INSERT INTO phrases (dataset_id, text, class_name, created_at) VALUES (?, ?, '', ?)",
        (dataset_id, key, now()),
    )
    phrase_id = int(cursor.lastrowid or 0)
    _write_members(connection, phrase_id, members)
    return phrase_id


def set_members(
    connection: sqlite3.Connection,
    dataset_id: str,
    phrase_id: int,
    text: str,
    classes: Iterable[str],
) -> None:
    _write_members(connection, phrase_id, _checked_members(connection, dataset_id, text, classes))


def _write_members(connection: sqlite3.Connection, phrase_id: int, members: list[str]) -> None:
    connection.execute("DELETE FROM phrase_classes WHERE phrase_id = ?", (phrase_id,))
    connection.executemany(
        "INSERT INTO phrase_classes (phrase_id, class_name) VALUES (?, ?)",
        [(phrase_id, member) for member in members],
    )


__all__ = ["MIN_MEMBERS", "add_umbrella", "class_keys", "members_of", "set_members"]
