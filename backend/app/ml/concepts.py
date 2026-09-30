"""The separate things a prompt asks for.

"flame, reflection" asks for two things, as does "flame. reflection." Grounding DINO only
separates phrases at a full stop, and SAM 3 reads its whole text as one concept, so a
comma used to make two search terms one label (found by Jan, 2026-09-30). Every model
reads its prompt through this one split.
"""

from __future__ import annotations

import re


def prompt_terms(prompt: str) -> list[str]:
    """Lower-cased terms, split at full stops, commas, semicolons and line breaks."""
    parts = (part.strip() for part in re.split(r"[.,;\n]", prompt.lower()))
    return list(dict.fromkeys(part for part in parts if part))


__all__ = ["prompt_terms"]


def term_spans(text: str, terms: list[str]) -> list[tuple[int, int]]:
    """Each term's character span in the normalised prompt ("a. b. c.")."""
    spans: list[tuple[int, int]] = []
    start = 0
    for term in terms:
        begin = text.index(term, start)
        spans.append((begin, begin + len(term)))
        start = begin + len(term)
    return spans


def best_terms(
    token_scores: list[list[float]],
    offsets: list[tuple[int, int]],
    spans: list[tuple[int, int]],
    terms: list[str],
) -> list[str]:
    """One term per box: the term whose tokens the box matched most strongly.

    Grounding DINO's own labels join every token above the text threshold, so a box can
    come back as "tree light" when both terms were asked (Jan, 2026-09-30). A box is one
    thing; it gets the term with the highest token score. `token_scores` is one row per
    box, one score per token position; `offsets` are the tokens' character offsets.
    """
    owners: list[list[int]] = [[] for _ in terms]
    for position, (begin, end) in enumerate(offsets):
        if end <= begin:
            continue
        for index, (low, high) in enumerate(spans):
            if low <= begin and end <= high:
                owners[index].append(position)
    labels: list[str] = []
    for row in token_scores:
        scores = [max((row[p] for p in owned if p < len(row)), default=-1.0) for owned in owners]
        labels.append(terms[scores.index(max(scores))])
    return labels
