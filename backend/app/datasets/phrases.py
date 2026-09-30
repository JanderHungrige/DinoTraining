"""A dataset's SAM 3 phrases and per-picture phrase statuses (doc 103).

The listing is stored phrases ∪ class names, the same union doc 60 uses for classes: a
class is its own default phrase, so a dataset annotated before phrases existed lists every
class as a phrase, with no migration.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Literal

from pydantic import BaseModel

from app.core.config import Settings
from app.datasets.class_names import normalise_class_name
from app.datasets.db import transaction
from app.datasets.phrase_links import check_variants, ensure_phrase, phrase_key, split_input

Status = Literal["complete", "absent"]


class PhraseInfo(BaseModel):
    #: None for a class's implicit phrase that has no row yet.
    id: int | None
    text: str
    class_name: str
    variants: list[str]
    confusable: list[str]
    #: Masks answering to it, a class's unlinked masks included for its own phrase.
    instances: int
    #: Pictures checked "all marked" / "not in this picture" for it.
    complete: int
    absent: int


class PictureStatus(BaseModel):
    phrase_id: int
    text: str
    status: Status


def _counts(connection: sqlite3.Connection, dataset_id: str) -> dict[str, dict[str, int]]:
    """Per phrase text: linked instances, implicit instances and statuses."""
    found: dict[str, dict[str, int]] = {}

    def bump(text: str, key: str, n: int) -> None:
        found.setdefault(text, {"instances": 0, "complete": 0, "absent": 0})[key] += n

    for row in connection.execute(
        "SELECT m.prompt, COUNT(*) AS n FROM masks m JOIN images i ON m.image_id = i.id"
        " WHERE i.dataset_id = ? AND m.label = 'positive' GROUP BY m.prompt",
        (dataset_id,),
    ):
        bump(phrase_key(row["prompt"] or ""), "instances", int(row["n"]))
    for row in connection.execute(
        "SELECT p.text, COUNT(*) AS n FROM mask_phrases mp JOIN phrases p ON p.id = mp.phrase_id"
        " JOIN masks m ON m.id = mp.mask_id WHERE p.dataset_id = ? AND m.label = 'positive'"
        " GROUP BY p.text",
        (dataset_id,),
    ):
        bump(str(row["text"]), "instances", int(row["n"]))
    for row in connection.execute(
        "SELECT p.text, s.status, COUNT(*) AS n FROM image_phrase_status s"
        " JOIN phrases p ON p.id = s.phrase_id WHERE p.dataset_id = ? GROUP BY p.text, s.status",
        (dataset_id,),
    ):
        bump(str(row["text"]), str(row["status"]), int(row["n"]))
    return found


class PhraseStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    def list_for(self, dataset_id: str) -> list[PhraseInfo]:
        with transaction(self._settings) as connection:
            rows = connection.execute(
                "SELECT * FROM phrases WHERE dataset_id = ? ORDER BY text", (dataset_id,)
            ).fetchall()
            counts = _counts(connection, dataset_id)
            classes = {
                str(row["prompt"] or "")
                for row in connection.execute(
                    "SELECT DISTINCT m.prompt FROM masks m JOIN images i ON m.image_id = i.id"
                    " WHERE i.dataset_id = ?",
                    (dataset_id,),
                )
            } | {
                str(row["name"])
                for row in connection.execute(
                    "SELECT name FROM dataset_classes WHERE dataset_id = ?", (dataset_id,)
                )
            }
        listed = {str(row["text"]): _info(row, counts) for row in rows}
        for name in classes:
            key = phrase_key(name)
            if key not in listed:
                listed[key] = PhraseInfo(
                    id=None,
                    text=key,
                    class_name=name or key,
                    variants=[],
                    confusable=[],
                    **counts.get(key, {"instances": 0, "complete": 0, "absent": 0}),
                )
        return sorted(listed.values(), key=lambda p: (normalise_class_name(p.class_name), p.text))

    def add(self, dataset_id: str, text: str, class_name: str | None = None) -> PhraseInfo:
        """`"red car, crimson car"` → phrase "red car" with a variation. An existing phrase
        gains the new variations rather than being refused."""
        main, variants = split_input(text)
        with transaction(self._settings) as connection:
            phrase_id = ensure_phrase(connection, dataset_id, main, class_name or main)
            row = connection.execute("SELECT * FROM phrases WHERE id = ?", (phrase_id,)).fetchone()
            merged = list(dict.fromkeys([*json.loads(row["variants"]), *variants]))
            check_variants(connection, dataset_id, main, merged)
            connection.execute(
                "UPDATE phrases SET variants = ? WHERE id = ?", (json.dumps(merged), phrase_id)
            )
        return self._one(dataset_id, phrase_id)

    def update(
        self,
        dataset_id: str,
        phrase_id: int,
        variants: list[str] | None = None,
        confusable: list[str] | None = None,
    ) -> PhraseInfo:
        with transaction(self._settings) as connection:
            row = connection.execute(
                "SELECT * FROM phrases WHERE id = ? AND dataset_id = ?", (phrase_id, dataset_id)
            ).fetchone()
            if row is None:
                raise LookupError(f"No such phrase: {phrase_id}")
            if variants is not None:
                clean = list(
                    dict.fromkeys(k for v in variants if (k := phrase_key(v)) != row["text"])
                )
                check_variants(connection, dataset_id, str(row["text"]), clean)
                connection.execute(
                    "UPDATE phrases SET variants = ? WHERE id = ?", (json.dumps(clean), phrase_id)
                )
            if confusable is not None:
                clean = list(dict.fromkeys(phrase_key(v) for v in confusable if v.strip()))
                connection.execute(
                    "UPDATE phrases SET confusable = ? WHERE id = ?", (json.dumps(clean), phrase_id)
                )
        return self._one(dataset_id, phrase_id)

    def delete(self, dataset_id: str, phrase_id: int) -> bool:
        with transaction(self._settings) as connection:
            cursor = connection.execute(
                "DELETE FROM phrases WHERE id = ? AND dataset_id = ?", (phrase_id, dataset_id)
            )
        return cursor.rowcount > 0

    def _one(self, dataset_id: str, phrase_id: int) -> PhraseInfo:
        return next(p for p in self.list_for(dataset_id) if p.id == phrase_id)


def _info(row: sqlite3.Row, counts: dict[str, dict[str, int]]) -> PhraseInfo:
    text = str(row["text"])
    return PhraseInfo(
        id=int(row["id"]),
        text=text,
        class_name=str(row["class_name"]),
        variants=json.loads(row["variants"]),
        confusable=json.loads(row["confusable"]),
        **counts.get(text, {"instances": 0, "complete": 0, "absent": 0}),
    )


__all__ = ["PhraseInfo", "PhraseStore", "PictureStatus", "Status"]
