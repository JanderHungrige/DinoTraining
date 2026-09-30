"""Phrases inside a transaction (doc 103): resolve, create, link, read back.

Connection-level so the mask write path can link inside the same transaction that
replaces the masks — a link written after a separate commit could point at a mask the next
save has already deleted.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable

from app.datasets.class_names import normalise_class_name
from app.datasets.images import now


def phrase_key(text: str) -> str:
    """A phrase as stored: class-name rules, and inner spaces collapsed."""
    return " ".join(normalise_class_name(text).split())


def split_input(text: str) -> tuple[str, list[str]]:
    """`"red car, crimson car"` → `("red car", ["crimson car"])`. Order kept, duplicates
    and empties dropped. `ValueError` when nothing is left."""
    seen: list[str] = []
    for part in text.split(","):
        if part.strip() and (key := phrase_key(part)) not in seen:
            seen.append(key)
    if not seen:
        raise ValueError("A phrase cannot be empty.")
    return seen[0], seen[1:]


def _row(connection: sqlite3.Connection, dataset_id: str, text: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = connection.execute(
        "SELECT * FROM phrases WHERE dataset_id = ? AND text = ?", (dataset_id, text)
    ).fetchone()
    return row


def variant_owner(connection: sqlite3.Connection, dataset_id: str, text: str) -> str | None:
    """The phrase that already lists `text` as a variant, if any."""
    for row in connection.execute(
        "SELECT text, variants FROM phrases WHERE dataset_id = ?", (dataset_id,)
    ):
        if text in json.loads(row["variants"]):
            return str(row["text"])
    return None


def check_variants(
    connection: sqlite3.Connection, dataset_id: str, text: str, variants: Iterable[str]
) -> None:
    """A variant must not be another phrase's text: one wording would train as two concepts."""
    for variant in variants:
        other = _row(connection, dataset_id, variant)
        if other is not None and other["text"] != text:
            raise ValueError(
                f"'{variant}' is already a phrase of its own; it cannot also be a variation "
                f"of '{text}'. Delete one, or merge them."
            )


def ensure_phrase(
    connection: sqlite3.Connection, dataset_id: str, text: str, class_name: str
) -> int:
    """The id of `text` in this dataset, created under `class_name` when missing.

    Refuses a phrase of another class: linking a mask of class A to class B's phrase is a
    labelling mistake, not a choice (doc 103, rule 1).
    """
    key = phrase_key(text)
    if not key:
        raise ValueError("A phrase cannot be empty.")
    row = _row(connection, dataset_id, key)
    if row is not None:
        if normalise_class_name(row["class_name"]) != normalise_class_name(class_name):
            raise ValueError(
                f"'{key}' is a phrase of class '{row['class_name']}', not '{class_name}'."
            )
        return int(row["id"])
    owner = variant_owner(connection, dataset_id, key)
    if owner is not None:
        raise ValueError(f"'{key}' is a variation of '{owner}'; use '{owner}' instead.")
    cursor = connection.execute(
        "INSERT INTO phrases (dataset_id, text, class_name, created_at) VALUES (?, ?, ?, ?)",
        (dataset_id, key, class_name, now()),
    )
    return int(cursor.lastrowid or 0)


def link_mask(
    connection: sqlite3.Connection,
    dataset_id: str,
    mask_id: int,
    class_name: str,
    phrases: Iterable[str],
) -> None:
    """Link a stored mask to its phrases. Its class's own name needs no link."""
    default = phrase_key(class_name)
    for text in phrases:
        if phrase_key(text) == default:
            continue
        phrase_id = ensure_phrase(connection, dataset_id, text, class_name)
        connection.execute(
            "INSERT OR IGNORE INTO mask_phrases (mask_id, phrase_id) VALUES (?, ?)",
            (mask_id, phrase_id),
        )


def phrases_of_masks(connection: sqlite3.Connection, mask_ids: list[int]) -> dict[int, list[str]]:
    """Each mask's linked phrase texts (its class name not included)."""
    if not mask_ids:
        return {}
    marks = ",".join("?" * len(mask_ids))
    found: dict[int, list[str]] = {}
    for row in connection.execute(
        f"SELECT mp.mask_id, p.text FROM mask_phrases mp JOIN phrases p ON p.id = mp.phrase_id"
        f" WHERE mp.mask_id IN ({marks}) ORDER BY p.text",
        mask_ids,
    ):
        found.setdefault(int(row["mask_id"]), []).append(str(row["text"]))
    return found


__all__ = [
    "check_variants",
    "ensure_phrase",
    "link_mask",
    "phrase_key",
    "phrases_of_masks",
    "split_input",
    "variant_owner",
]
