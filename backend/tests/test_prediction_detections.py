"""Tests for Prediction.detections() — the sanctioned reader for boxes+scores+classes.

The payload's three arrays are only meaningful together: boxes_payload drops a zero-area
box from all three at once so they stay aligned. Every consumer that reads them by raw key
is a chance to pair box *i* with score *j*, which produces a plausible-looking annotation
carrying the wrong confidence and class — a mislabel that no shape check would catch.
"""

from __future__ import annotations

from app.ml.inference.results import Prediction


def prediction(**payload: object) -> Prediction:
    return Prediction(
        instance_id="i",
        head_name="Detector",
        head_type_id="dense-detector",
        task="detection",
        render_hint="boxes",
        class_names=("bolt", "nut"),
        payload=payload,
    )


class TestDetections:
    def test_it_zips_the_three_arrays_positionally(self) -> None:
        result = prediction(
            boxes=[[0, 0, 10, 10], [5, 5, 20, 20]],
            scores=[0.9, 0.4],
            classes=[0, 1],
        ).detections()

        assert result == [
            ((0.0, 0.0, 10.0, 10.0), 0.9, "bolt"),
            ((5.0, 5.0, 20.0, 20.0), 0.4, "nut"),
        ]

    def test_an_empty_payload_yields_nothing(self) -> None:
        assert prediction().detections() == []

    def test_no_detections_yields_an_empty_list(self) -> None:
        assert prediction(boxes=[], scores=[], classes=[]).detections() == []

    def test_a_class_index_beyond_the_name_list_gets_a_placeholder(self) -> None:
        """A pretrained default can carry indices with no names attached."""
        result = prediction(boxes=[[0, 0, 1, 1]], scores=[0.5], classes=[99]).detections()
        assert result[0][2] == "class 99"

    def test_misaligned_arrays_return_nothing_rather_than_guessing(self) -> None:
        """Not a recoverable state: it means something other than boxes_payload built it.

        Returning the shorter zip would silently attach the wrong score and class to every
        box after the mismatch — a wrong answer is worse here than no answer.
        """
        misaligned = prediction(
            boxes=[[0, 0, 1, 1], [1, 1, 2, 2]], scores=[0.5], classes=[0]
        )
        assert misaligned.detections() == []

    def test_a_missing_scores_array_returns_nothing(self) -> None:
        assert prediction(boxes=[[0, 0, 1, 1]], classes=[0]).detections() == []

    def test_a_missing_classes_array_returns_nothing(self) -> None:
        assert prediction(boxes=[[0, 0, 1, 1]], scores=[0.5]).detections() == []

    def test_boxes_property_still_works_for_the_viewer(self) -> None:
        """The viewer needs only the box; detections() did not replace it."""
        assert prediction(boxes=[[1, 2, 3, 4]]).boxes == [(1.0, 2.0, 3.0, 4.0)]
