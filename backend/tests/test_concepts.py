"""A prompt's separate terms, and one term per Grounding DINO box (Jan, 2026-09-30)."""

from __future__ import annotations

from app.ml.concepts import best_terms, prompt_terms, term_spans


def test_commas_periods_and_lines_separate_terms_once_each() -> None:
    assert prompt_terms("Flame, flame reflection. flame\n") == ["flame", "flame reflection"]


def test_each_box_gets_the_single_term_it_matched_most() -> None:
    """Grounding DINO labelled such boxes "tree light": every token above the text
    threshold, across two terms. A box is one thing."""
    text = "tree. light."
    terms = ["tree", "light"]
    # Tokens: [CLS], tree, ., light, ., [SEP]
    offsets = [(0, 0), (0, 4), (4, 5), (6, 11), (11, 12), (0, 0)]
    scores = [
        [0.0, 0.6, 0.1, 0.4, 0.1, 0.0],  # both above 0.25; tree wins
        [0.0, 0.3, 0.1, 0.9, 0.1, 0.0],  # light wins
    ]
    assert term_spans(text, terms) == [(0, 4), (6, 11)]
    assert best_terms(scores, offsets, term_spans(text, terms), terms) == ["tree", "light"]


def test_a_term_that_contains_another_is_located_in_order() -> None:
    text = "flame. flame reflection."
    assert term_spans(text, ["flame", "flame reflection"]) == [(0, 5), (7, 23)]
