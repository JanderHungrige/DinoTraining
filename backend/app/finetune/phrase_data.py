"""What SAM 3 training reads about phrases (doc 108): wordings, look-alikes, which outline
answers to which phrase, and which pictures were checked for which phrase.

Read once per job from the store, keyed so the sample set (which carries class-mapped
masks, doc 90) can be joined to it: an outline by its run lengths, a picture by its path.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.masks import MaskStore
from app.datasets.phrase_links import phrase_key
from app.datasets.phrases import PhraseStore

RleKey = tuple[int, ...]


@dataclass
class PhraseDef:
    text: str
    class_name: str
    variants: tuple[str, ...] = ()
    confusable: tuple[str, ...] = ()


@dataclass
class PhraseTable:
    phrases: dict[str, PhraseDef] = field(default_factory=dict)
    #: path → phrase → "complete" | "absent".
    statuses: dict[str, dict[str, str]] = field(default_factory=dict)
    #: path → run lengths of an accepted outline → the phrases linked to it (class excluded).
    linked: dict[str, dict[RleKey, tuple[str, ...]]] = field(default_factory=dict)
    #: path → phrases with a rejected outline on that picture.
    rejected: dict[str, set[str]] = field(default_factory=dict)

    @property
    def checked_phrases(self) -> set[str]:
        """Phrases checked on at least one picture. Per phrase, not per dataset (doc 108,
        amended): checking one picture for "signal" must not take the automatic negatives
        away from every other phrase — or from every other picture of a dataset where only
        one was checked by way of trying it out."""
        return {text for marks in self.statuses.values() for text in marks}

    def vocabulary(self) -> set[str]:
        words: set[str] = set()
        for phrase in self.phrases.values():
            for text in (phrase.text, *phrase.variants, *phrase.confusable):
                words.update(text.split())
        return words


def load_phrase_table(
    dataset_ids: tuple[str, ...], settings: Settings | None = None
) -> PhraseTable:
    table = PhraseTable()
    masks = MaskStore(settings)
    for dataset_id in dataset_ids:
        for info in PhraseStore(settings).list_for(dataset_id):
            table.phrases.setdefault(
                info.text,
                PhraseDef(info.text, info.class_name, tuple(info.variants), tuple(info.confusable)),
            )
        with transaction(settings) as connection:
            rows = connection.execute(
                "SELECT i.path, p.text, s.status FROM image_phrase_status s"
                " JOIN images i ON i.id = s.image_id JOIN phrases p ON p.id = s.phrase_id"
                " WHERE i.dataset_id = ?",
                (dataset_id,),
            ).fetchall()
        for row in rows:
            table.statuses.setdefault(str(row["path"]), {})[str(row["text"])] = str(row["status"])
        for _, path, _, _, stored in masks.image_masks(dataset_id):
            for mask in stored:
                own = phrase_key(mask.prompt or "")
                if mask.label == "negative":
                    table.rejected.setdefault(path, set()).update(mask.phrases or [own])
                elif mask.label == "positive":
                    extra = tuple(p for p in mask.phrases if p != own)
                    if extra:
                        table.linked.setdefault(path, {})[tuple(mask.rle.counts)] = extra
    return table


__all__ = ["PhraseDef", "PhraseTable", "RleKey", "load_phrase_table"]
