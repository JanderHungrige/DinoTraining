"""Which phrase queries a picture teaches SAM 3 in one round (docs 108, 115, 117).

Pure: a sample, the phrase table and the settings in; the queries out. A saved picture is
complete for the classes that existed when it was saved (doc 117); a class added later is
left out on the pictures saved before it, unless they were checked by hand — an instance
nobody looked for is not "none here".
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from app.datasets.phrase_links import phrase_key
from app.finetune.phrase_data import PhraseTable
from app.ml.training.samples import TrainingSample

#: Everyday concepts asked as "none here" (SAM3_LoRA's generic negatives). Any that shares
#: a word with the dataset's own phrases is left out.
GENERIC_POOL = (
    "car", "person", "dog", "cat", "bicycle", "tree", "chair", "bottle", "cup", "book",
    "bird", "horse", "boat", "airplane", "bus", "train", "truck", "motorcycle", "traffic light",
    "bench", "umbrella", "backpack", "phone", "laptop", "keyboard", "clock", "vase", "banana",
    "apple", "pizza", "cake", "couch", "bed", "toilet", "sink", "oven", "window", "door",
    "shoe", "hat",
)  # fmt: skip
#: SAM3_LoRA: with more phrases than this, cross negatives are sampled instead of all used.
MANY_PHRASES = 50


@dataclass(frozen=True)
class QuerySettings:
    num_negatives: int = 3
    num_cross_negatives: int = 2
    all_variations: bool = False
    rejected_as_negatives: bool = True


@dataclass(frozen=True)
class Query:
    #: The wording asked.
    text: str
    #: Indices into the sample's masks that answer to it; empty for a negative.
    masks: tuple[int, ...]
    #: positive | absent | cross | rejected | confusable | generic
    kind: str


def _mask_phrases(
    sample: TrainingSample, names: tuple[str, ...], table: PhraseTable
) -> list[set[str]]:
    linked = table.linked.get(sample.path, {})
    return [
        {phrase_key(names[m.class_index]), *linked.get(tuple(m.counts), ())} for m in sample.masks
    ]


def _wordings(table: PhraseTable, text: str) -> tuple[str, ...]:
    phrase = table.phrases.get(text)
    return (text, *phrase.variants) if phrase else (text,)


def _worded(
    query: Query, table: PhraseTable, settings: QuerySettings, rng: random.Random, evaluation: bool
) -> list[Query]:
    if evaluation or query.kind in ("generic", "confusable"):
        return [query]
    words = _wordings(table, query.text)
    if settings.all_variations:
        return [Query(word, query.masks, query.kind) for word in words]
    return [Query(rng.choice(words), query.masks, query.kind)]


def _looks(
    text: str, sample: TrainingSample, table: PhraseTable, answers: dict[str, tuple[int, ...]]
) -> list[Query]:
    """A positive phrase's look-alikes, each a "none here". Not on a picture with a rejected
    outline of it: the look-alike may well be there (a flame's reflection)."""
    phrase = table.phrases.get(text)
    if phrase is None or text in table.rejected.get(sample.path, ()):
        return []
    return [Query(look, (), "confusable") for look in phrase.confusable if look not in answers]


class _Picture:
    """One picture's facts for the query decisions: explicit checks, unknown classes
    (doc 117), unclear outlines and rejections."""

    def __init__(self, sample: TrainingSample, table: PhraseTable, doubtful: set[str]) -> None:
        self.status = table.statuses.get(sample.path, {})
        self.unknown = table.unknown.get(sample.path, set())
        self.rejected = table.rejected.get(sample.path, set())
        self.doubtful = doubtful
        self.table = table

    def known(self, text: str) -> bool:
        """Whether this picture's answer for `text` can be trusted: checked by hand, or
        saved after its class existed. A sub-phrase follows its class."""
        if self.status.get(text) in ("complete", "absent"):
            return True
        phrase = self.table.phrases.get(text)
        own = phrase_key(phrase.class_name) if phrase and phrase.class_name else text
        return text not in self.unknown and own not in self.unknown


def _pairs(
    sample: TrainingSample, names: tuple[str, ...], table: PhraseTable, settings: QuerySettings
) -> tuple[list[Query], list[Query]]:
    """(positives and explicit/rejected negatives, in-domain negatives subject to the cap).

    Doc 117: a picture teaches a class it is *known* for — checked by hand, or saved after
    the class existed. Doc 109: a phrase with an *unclear* outline here is never a negative.
    Umbrella terms (doc 115) follow their members.
    """
    per_mask = _mask_phrases(sample, names, table)
    here = _Picture(sample, table, {phrase_key(names[m.class_index]) for m in sample.ignore_masks})
    classes = [phrase_key(name) for name in names]
    umbrellas = {t: p.classes for t, p in table.phrases.items() if p.classes}
    texts = list(dict.fromkeys([*classes, *(t for t in table.phrases if t not in umbrellas)]))
    answers = {t: tuple(i for i, found in enumerate(per_mask) if t in found) for t in texts}
    taught: list[Query] = []
    negatives: list[Query] = []
    for text in texts:
        found = answers[text]
        state = here.status.get(text)
        if state == "absent" and text not in here.doubtful:
            negatives.append(Query(text, (), "absent"))
        elif found and here.known(text):
            taught.append(Query(text, found, "positive"))
            taught += _looks(text, sample, table, answers)
        elif found or text in here.doubtful or state == "complete":
            # Outlines on a picture never looked at for it, doubt, or "all marked" with no
            # outline (a contradiction): skipped rather than guessed either way.
            continue
        elif here.known(text):
            if text in classes:
                negatives.append(Query(text, (), "cross"))
        elif settings.rejected_as_negatives and text in here.rejected:
            taught.append(Query(text, (), "rejected"))
    for text, members in umbrellas.items():
        query = _umbrella(text, members, answers, here)
        if query is not None:
            (negatives if query.kind in ("cross", "absent") else taught).append(query)
            if query.kind == "positive":
                taught += _looks(text, sample, table, answers)
    return taught, negatives


def _umbrella(
    text: str, members: tuple[str, ...], answers: dict[str, tuple[int, ...]], here: _Picture
) -> Query | None:
    """An umbrella's query on one picture, from its members' state (doc 115).

    Only when every member's answer here is known: a member never looked at here, or
    unclear here, leaves the umbrella out — a partial answer would teach that the
    unoutlined screws are not screws.
    """

    def known(member: str) -> bool:
        if member in here.doubtful:
            return False
        if here.status.get(member) == "complete" and not answers.get(member):
            return False
        return here.known(member)

    if not all(known(m) for m in members):
        return None
    found = tuple(sorted({i for m in members for i in answers.get(m, ())}))
    if found:
        return Query(text, found, "positive")
    checked = any(here.status.get(m) == "absent" for m in members)
    return Query(text, (), "absent" if checked else "cross")


def plan_queries(
    sample: TrainingSample,
    names: tuple[str, ...],
    table: PhraseTable,
    settings: QuerySettings,
    rng: random.Random,
    evaluation: bool = False,
) -> list[Query]:
    taught, negatives = _pairs(sample, names, table, settings)
    many = len(set(names) | set(table.phrases)) > MANY_PHRASES
    if many and not evaluation and len(negatives) > settings.num_cross_negatives:
        negatives = rng.sample(negatives, settings.num_cross_negatives)
    planned = [*taught, *negatives]
    if not evaluation:
        taken = table.vocabulary() | {w for n in names for w in phrase_key(n).split()}
        pool = [c for c in GENERIC_POOL if not set(c.split()) & taken]
        count = min(settings.num_negatives, len(pool))
        planned += [Query(c, (), "generic") for c in rng.sample(pool, count)] if count else []
    return [
        worded for query in planned for worded in _worded(query, table, settings, rng, evaluation)
    ]


def describe(counts: Counter[str], rounds: int) -> str:
    """The job note: what SAM 3 trained on, per round."""
    per = {kind: n // max(1, rounds) for kind, n in counts.items()}
    negatives = sum(n for kind, n in per.items() if kind != "positive")
    parts = ", ".join(
        f"{per.get(k, 0)} {k}" for k in ("absent", "cross", "rejected", "confusable", "generic")
    )
    positives = per.get("positive", 0)
    return (
        f"SAM 3 trained on {positives} positive queries and {negatives} negatives "
        f"per round: {parts}."
    )


__all__ = ["GENERIC_POOL", "Query", "QuerySettings", "describe", "plan_queries"]
