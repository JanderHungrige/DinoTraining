"""Tests for COCO run-length encoding.

Column-major order with a leading zero-run is the COCO convention. A row-major encoding
round-trips perfectly against its own decoder and is silently wrong to every other reader,
so the orientation is asserted against hand-computed values rather than only via round-trip.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.datasets.rle import (
    rle_area,
    rle_bbox,
    rle_decode,
    rle_encode,
    validate_counts,
)


def _mask(rows: list[str]) -> np.ndarray:
    """Build a mask from '.'/'#' art, so the expected encoding is readable in the test."""
    return np.array([[c == "#" for c in row] for row in rows], dtype=bool)


class TestEncode:
    def test_an_empty_mask_is_one_run_of_zeros(self) -> None:
        counts, size = rle_encode(np.zeros((3, 4), dtype=bool))
        assert size == (3, 4)
        assert counts == [12]

    def test_a_full_mask_starts_with_a_zero_length_run(self) -> None:
        """COCO always starts counting from background, so a full mask leads with 0."""
        counts, _ = rle_encode(np.ones((2, 3), dtype=bool))
        assert counts == [0, 6]

    def test_it_encodes_column_major_not_row_major(self) -> None:
        # 2x2 with only the top-right pixel set.
        #   . #
        #   . .
        # Column-major order visits (0,0),(1,0),(0,1),(1,1) -> F F T F
        # so the runs are 2 background, 1 foreground, 1 background.
        counts, size = rle_encode(_mask([".#", ".."]))
        assert size == (2, 2)
        assert counts == [2, 1, 1]

    def test_run_lengths_sum_to_the_pixel_count(self) -> None:
        counts, size = rle_encode(_mask(["#.#", ".#.", "##."]))
        assert sum(counts) == size[0] * size[1] == 9


class TestRoundTrip:
    @pytest.mark.parametrize(
        "art",
        [
            ["...", "...", "..."],
            ["###", "###", "###"],
            ["#.#", ".#.", "#.#"],
            ["..#", ".##", "###"],
            ["#..", "...", "..#"],
        ],
    )
    def test_decode_inverts_encode(self, art: list[str]) -> None:
        original = _mask(art)
        counts, size = rle_encode(original)
        assert np.array_equal(rle_decode(counts, size), original)

    def test_it_round_trips_a_non_square_mask(self) -> None:
        """A height/width mix-up survives every square test and fails here."""
        original = _mask(["#....", ".##..", "....#"])
        counts, size = rle_encode(original)
        assert size == (3, 5)
        assert np.array_equal(rle_decode(counts, size), original)


class TestBbox:
    def test_it_returns_xywh_top_left(self) -> None:
        # Set pixels at rows 1-2, cols 2-3.
        bbox = rle_bbox(*rle_encode(_mask(["....", "..##", "..##"])))
        assert bbox == (2.0, 1.0, 2.0, 2.0)

    def test_a_single_pixel_has_width_and_height_one(self) -> None:
        assert rle_bbox(*rle_encode(_mask(["...", ".#.", "..."]))) == (1.0, 1.0, 1.0, 1.0)

    def test_an_empty_mask_has_no_bbox(self) -> None:
        assert rle_bbox(*rle_encode(np.zeros((4, 4), dtype=bool))) is None


class TestArea:
    def test_it_counts_foreground_pixels(self) -> None:
        counts, _ = rle_encode(_mask(["#.#", ".#.", "..."]))
        assert rle_area(counts) == 3

    def test_an_empty_mask_has_zero_area(self) -> None:
        counts, _ = rle_encode(np.zeros((5, 5), dtype=bool))
        assert rle_area(counts) == 0


class TestValidateCounts:
    def test_it_accepts_counts_that_sum_to_the_frame(self) -> None:
        validate_counts([2, 1, 1], 2, 2)

    def test_it_rejects_a_short_encoding(self) -> None:
        with pytest.raises(ValueError, match="sum"):
            validate_counts([2, 1], 2, 2)

    def test_it_rejects_an_overflowing_encoding(self) -> None:
        """The guard is arithmetic on the list — no mask is allocated to find this out."""
        with pytest.raises(ValueError, match="sum"):
            validate_counts([10_000_000], 2, 2)

    def test_it_rejects_a_negative_run(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            validate_counts([5, -1], 2, 2)
