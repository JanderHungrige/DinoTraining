"""Which phrase queries a picture teaches SAM 3 in one round (doc 108).

Pure: a sample, the phrase table and the settings in; the queries out. A phrase never
checked on any picture trains as before doc 108; once a phrase is checked somewhere, only
its checked pictures teach it — an unannotated instance is not "none here".
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


def _pairs(
    sample: TrainingSample, names: tuple[str, ...], table: PhraseTable, settings: QuerySettings
) -> tuple[list[Query], list[Query]]:
    """(positives and explicit/rejected negatives, in-domain negatives subject to the cap).

    Doc 109: a phrase with an *unclear* outline on the picture is never a negative there —
    the annotator's doubt is not "none here".
    """
    per_mask = _mask_phrases(sample, names, table)
    doubtful = {phrase_key(names[m.class_index]) for m in sample.ignore_masks}
    classes = [phrase_key(name) for name in names]
    texts = list(dict.fromkeys([*classes, *table.phrases]))
    answers = {t: tuple(i for i, found in enumerate(per_mask) if t in found) for t in texts}
    taught: list[Query] = []
    negatives: list[Query] = []
    checked = table.checked_phrases
    status = table.statuses.get(sample.path, {})
    for text in texts:
        found = answers[text]
        if text not in checked:
            # Never checked anywhere: as before doc 108 — its outlines teach, and a class
            # without one here is "none here".
            if found:
                taught.append(Query(text, found, "positive"))
            elif text in classes and text not in doubtful:
                negatives.append(Query(text, (), "cross"))
            continue
        state = status.get(text)
        if state == "complete" and found:
            taught.append(Query(text, found, "positive"))
            phrase = table.phrases.get(text)
            for look in phrase.confusable if phrase else ():
                if look not in answers:
                    taught.append(Query(look, (), "confusable"))
        elif text in doubtful:
            continue
        elif state == "absent":
            negatives.append(Query(text, (), "absent"))
        elif state == "complete":
            # "All marked" with no outline answering to it contradicts itself (a link
            # missing?): skipped rather than guessed either way.
            continue
        elif (
            settings.rejected_as_negatives
            and not found
            and text in table.rejected.get(sample.path, ())
        ):
            taught.append(Query(text, (), "rejected"))
    return taught, negatives


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
