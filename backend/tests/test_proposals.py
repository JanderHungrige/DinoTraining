"""Clamping a proposed box to the frame (doc 42).

Detectors predict boxes that leave the image, legitimately: an object touching an edge
continues past it and the model has no reason to stop at the border. `Box` requires
`x >= 0` and `fits_within`, so an unclamped proposal raises on the way into the store —
*after* the reviewer has judged it, which is the worst moment to lose work.

Measured, not hypothesised: RF-DETR returned a `couch` box beginning at x=0.9 and running
1.5 px past the right edge of a 640x480 image (doc 41).
"""

from __future__ import annotations

import pytest

from app.datasets.models import Box
from app.ml.annotators.proposals import PROPOSED_LABEL, clamp_to_frame


class TestClampToFrame:
    def test_a_box_inside_the_frame_is_untouched(self) -> None:
        assert clamp_to_frame((10.0, 20.0, 30.0, 40.0), 100, 100) == (10.0, 20.0, 30.0, 40.0)

    def test_it_trims_the_measured_rf_detr_overhang(self) -> None:
        # The real case: 1.5 px past the right edge of a 640x480 image.
        clamped = clamp_to_frame((0.9, 1.0, 640.6, 474.0), 640, 480)
        assert clamped is not None
        x, y, w, h = clamped
        assert x + w == pytest.approx(640.0)
        assert y + h == pytest.approx(475.0)

    def test_a_negative_origin_is_pulled_to_zero(self) -> None:
        # `Box` requires x >= 0, so a box starting off the left edge raises unclamped.
        clamped = clamp_to_frame((-5.0, -3.0, 20.0, 20.0), 100, 100)
        assert clamped == (0.0, 0.0, 15.0, 17.0)

    def test_it_clamps_all_four_edges_at_once(self) -> None:
        assert clamp_to_frame((-10.0, -10.0, 200.0, 200.0), 50, 40) == (0.0, 0.0, 50.0, 40.0)

    def test_a_box_entirely_outside_is_dropped(self) -> None:
        # Nothing left for a reviewer to look at, and `Box` would reject a zero-area one.
        assert clamp_to_frame((200.0, 200.0, 10.0, 10.0), 100, 100) is None

    def test_a_box_clamped_to_a_line_is_dropped(self) -> None:
        # Touching the edge exactly: width collapses to zero, which is not a box.
        assert clamp_to_frame((100.0, 10.0, 20.0, 20.0), 100, 100) is None

    def test_an_edge_object_is_kept_rather_than_dropped(self) -> None:
        """The reason clamping beats dropping: half a person at the frame edge is a real
        detection, and the visible half is exactly what a reviewer can judge."""
        clamped = clamp_to_frame((-30.0, 10.0, 60.0, 80.0), 640, 480)
        assert clamped == (0.0, 10.0, 30.0, 80.0)

    @pytest.mark.parametrize(
        "box",
        [
            (-5.0, -3.0, 20.0, 20.0),
            (0.9, 1.0, 640.6, 474.0),
            (630.0, 470.0, 40.0, 40.0),
        ],
    )
    def test_whatever_survives_is_always_constructible_as_a_box(
        self, box: tuple[float, float, float, float]
    ) -> None:
        """The point of the whole helper: the result must never make `Box` raise."""
        clamped = clamp_to_frame(box, 640, 480)
        if clamped is None:
            return
        built = Box(
            label=PROPOSED_LABEL,
            provenance="foundation-model",
            x=clamped[0],
            y=clamped[1],
            w=clamped[2],
            h=clamped[3],
        )
        assert built.fits_within(640, 480)
