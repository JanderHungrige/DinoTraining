"""Brush and eraser (doc 106): exact discs, no gaps, nothing outside the picture."""

from __future__ import annotations

import numpy as np
import pytest

from app.ml.mask_strokes import apply_stroke


def test_one_click_is_one_disc() -> None:
    painted = apply_stroke(np.zeros((21, 21), dtype=bool), [(10.5, 10.5)], 3, erase=False)
    assert painted[10, 10] and painted[10, 13] and not painted[10, 14]
    assert 25 <= painted.sum() <= 32  # about pi * 3^2


def test_a_fast_drag_leaves_no_gap() -> None:
    painted = apply_stroke(np.zeros((10, 100), dtype=bool), [(2, 5), (97, 5)], 2, erase=False)
    assert painted[5, 2:98].all()


def test_the_eraser_removes_and_never_adds() -> None:
    full = np.ones((10, 10), dtype=bool)
    erased = apply_stroke(full, [(5, 5)], 2, erase=True)
    assert not erased[5, 5] and erased[0, 0]
    assert not apply_stroke(np.zeros((10, 10), dtype=bool), [(5, 5)], 2, erase=True).any()


def test_a_stroke_off_the_edge_is_clipped_and_the_input_untouched() -> None:
    blank = np.zeros((10, 10), dtype=bool)
    painted = apply_stroke(blank, [(-5, -5), (0, 0)], 3, erase=False)
    assert painted[0, 0] and not blank.any()


def test_a_zero_brush_is_refused() -> None:
    with pytest.raises(ValueError, match="above zero"):
        apply_stroke(np.zeros((4, 4), dtype=bool), [(1, 1)], 0, erase=False)
