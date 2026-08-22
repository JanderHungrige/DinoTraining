"""Tests for the output decoders.

This registry exists because integration testing found metrics being handed raw
per-cell logits when they expected decoded boxes — the unit tests had fed the metric
function pre-decoded fixtures, so nothing caught the missing step.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.heads.decode import (
    DECODERS,
    MAX_DETECTIONS,
    decode_for,
    detection_decode,
)
from app.ml.heads.registry import HeadTypeSpec, all_head_types, get_head_type


def spec_for(head_id: str):  # type: ignore[no-untyped-def]
    found = get_head_type(head_id)
    assert found is not None
    return found


def detector_outputs(rows: int = 4, cols: int = 4, num_classes: int = 3) -> dict[str, torch.Tensor]:
    return {
        "class_logits": torch.randn(1, num_classes, rows, cols),
        "box_ltrb": torch.rand(1, 4, rows, cols) * 20 + 5,
        "centerness": torch.randn(1, 1, rows, cols),
    }


class TestDecoderRegistry:
    def test_every_head_type_has_a_decoder(self) -> None:
        """All seven, not just the trainable three.

        The table covered only trainable heads while it lived under training/, because
        the loop is the only caller that filters that way. Inference serves every usable
        head — including the pretrained defaults — so a missing entry is now a crash in
        the viewer rather than an unreachable branch.
        """
        missing = [entry.id for entry in all_head_types() if entry.id not in DECODERS]
        assert missing == []

    def test_every_trainable_head_has_a_decoder(self) -> None:
        """A missing decoder is a runtime failure at the first validation epoch."""
        for entry in all_head_types():
            if entry.trainable:
                assert decode_for(entry) is not None, entry.id

    def test_identity_decoders_pass_logits_through(self) -> None:
        outputs = {"logits": torch.randn(1, 3)}
        assert decode_for(spec_for("linear-classifier"))(outputs, 14) is outputs

    def test_segmentation_is_identity(self) -> None:
        outputs = {"logits": torch.randn(1, 3, 4, 4)}
        assert decode_for(spec_for("linear-segmenter"))(outputs, 14) is outputs


class TestDetectionDecode:
    def test_produces_the_keys_metrics_require(self) -> None:
        """The exact mismatch integration testing surfaced."""
        decoded = detection_decode(detector_outputs(), 14)
        assert set(decoded) == {"boxes", "scores", "classes"}

    def test_the_three_outputs_agree_on_length(self) -> None:
        """Not one entry per cell — NMS collapses duplicates, so only agreement holds."""
        decoded = detection_decode(detector_outputs(rows=4, cols=4), 14)
        count = decoded["boxes"].shape[0]
        assert 0 < count <= 16
        assert decoded["scores"].shape == (count,)
        assert decoded["classes"].shape == (count,)

    def test_caps_detections_on_a_large_grid(self) -> None:
        """Every cell of a 32x32 grid would make average_precision quadratic for no gain."""
        decoded = detection_decode(detector_outputs(rows=32, cols=32), 14)
        assert decoded["scores"].shape == (MAX_DETECTIONS,)

    def test_scores_are_probabilities(self) -> None:
        decoded = detection_decode(detector_outputs(), 14)
        assert bool((decoded["scores"] >= 0).all() and (decoded["scores"] <= 1).all())

    def test_scores_are_ranked_descending(self) -> None:
        scores = detection_decode(detector_outputs(rows=8, cols=8), 14)["scores"]
        assert torch.equal(scores, torch.sort(scores, descending=True).values)

    def test_centerness_suppresses_a_cell(self) -> None:
        """Confident cells near a box edge produce badly-placed boxes; centerness is
        what stops them dominating the ranking."""
        outputs = detector_outputs(rows=1, cols=2, num_classes=1)
        outputs["class_logits"][0, 0, 0, :] = 5.0  # both cells equally confident
        outputs["centerness"][0, 0, 0, 0] = 5.0
        outputs["centerness"][0, 0, 0, 1] = -5.0
        decoded = detection_decode(outputs, 14)
        assert decoded["scores"][0] > decoded["scores"][1]

    def test_classes_are_valid_indices(self) -> None:
        decoded = detection_decode(detector_outputs(num_classes=3), 14)
        assert bool((decoded["classes"] >= 0).all() and (decoded["classes"] < 3).all())

    def test_boxes_have_positive_extent(self) -> None:
        decoded = detection_decode(detector_outputs(), 14)
        assert bool((decoded["boxes"][:, 2] > 0).all())
        assert bool((decoded["boxes"][:, 3] > 0).all())

    def test_unknown_head_type_raises(self) -> None:
        """A missing decoder must raise, not silently fall back to identity.

        This used `linear-depth` as its example of an unregistered type; depth now has
        a decoder, so the example is a fabricated spec instead. The behaviour under
        test is unchanged — silently returning identity for an unknown head would ship
        raw per-cell logits to a renderer expecting boxes.
        """
        unregistered = HeadTypeSpec(
            id="not-registered-anywhere",
            task="classification",
            title="Fabricated",
            description="Exists only to prove decode_for refuses the unknown.",
            trainable=False,
            target_format=None,
            consumes="cls",
            geometry="center-crop",
            metrics=("accuracy",),
            primary_metric=None,
            primary_metric_mode=None,
            render_hint="labels",
            compatible_families=frozenset({"dinov2"}),
        )
        with pytest.raises(LookupError):
            decode_for(unregistered)


def _all_cells_on_one_box(
    box: tuple[float, float, float, float],
    rows: int = 4,
    cols: int = 4,
    patch: int = 14,
    num_classes: int = 2,
    class_index: int = 0,
) -> dict[str, torch.Tensor]:
    """Head outputs where **every** cell regresses to the same box.

    This is what a real detector does around an object: each patch whose receptive field
    covers it predicts that same object. Reproducing it exactly is the only way to test
    duplicate suppression — random fixtures overlap by accident and prove nothing.
    """
    x0, y0, width, height = box
    ltrb = torch.zeros(1, 4, rows, cols)
    for row in range(rows):
        for col in range(cols):
            centre_x = (col + 0.5) * patch
            centre_y = (row + 0.5) * patch
            ltrb[0, :, row, col] = torch.tensor(
                [centre_x - x0, centre_y - y0, x0 + width - centre_x, y0 + height - centre_y]
            )
    class_logits = torch.full((1, num_classes, rows, cols), -10.0)
    class_logits[0, class_index] = 3.0
    return {
        "class_logits": class_logits,
        "box_ltrb": ltrb,
        "centerness": torch.full((1, 1, rows, cols), 2.0),
    }


class TestDuplicateSuppression:
    """The bug doc 31 found by running a trained detector on a real image.

    The head type has advertised "NMS at inference" since Wave 2 and nothing implemented
    it, so one thermal person came back as 32 overlapping boxes. Every duplicate past the
    first is a false positive, so this cluttered the review UI *and* depressed `map`.
    """

    def test_sixteen_cells_naming_one_object_collapse_to_one_box(self) -> None:
        decoded = detection_decode(_all_cells_on_one_box((0, 0, 56, 56)), 14)
        assert decoded["boxes"].shape[0] == 1

    def test_the_surviving_box_is_the_object(self) -> None:
        decoded = detection_decode(_all_cells_on_one_box((0, 0, 56, 56)), 14)
        x, y, w, h = decoded["boxes"][0].tolist()
        assert (round(x), round(y), round(w), round(h)) == (0, 0, 56, 56)

    def test_two_separate_objects_both_survive(self) -> None:
        """Suppression must remove duplicates, not second detections."""
        left = _all_cells_on_one_box((0, 0, 20, 20), rows=1, cols=2)
        far = _all_cells_on_one_box((200, 200, 20, 20), rows=1, cols=2)
        merged = {
            "class_logits": torch.cat([left["class_logits"], far["class_logits"]], dim=3),
            "box_ltrb": torch.cat([left["box_ltrb"], far["box_ltrb"]], dim=3),
            "centerness": torch.cat([left["centerness"], far["centerness"]], dim=3),
        }
        decoded = detection_decode(merged, 14)
        assert decoded["boxes"].shape[0] == 2

    def test_overlapping_boxes_of_different_classes_both_survive(self) -> None:
        """Class-aware, deliberately: a dog in front of a person genuinely overlaps, and
        global NMS would delete whichever scored lower."""
        dog = _all_cells_on_one_box((0, 0, 56, 56), rows=2, cols=2, class_index=0)
        person = _all_cells_on_one_box((0, 0, 56, 56), rows=2, cols=2, class_index=1)
        merged = {
            "class_logits": torch.cat([dog["class_logits"], person["class_logits"]], dim=3),
            "box_ltrb": torch.cat([dog["box_ltrb"], person["box_ltrb"]], dim=3),
            "centerness": torch.cat([dog["centerness"], person["centerness"]], dim=3),
        }
        decoded = detection_decode(merged, 14)
        assert sorted(decoded["classes"].tolist()) == [0, 1]

    def test_the_highest_scoring_duplicate_wins(self) -> None:
        """NMS keeps the most confident of a cluster, not an arbitrary member."""
        outputs = _all_cells_on_one_box((0, 0, 56, 56))
        outputs["class_logits"][0, 0, 2, 2] = 9.0  # one cell far more confident
        decoded = detection_decode(outputs, 14)

        # sigmoid(9) * sigmoid(2) — centerness caps the product below 1, which is why
        # the assertion is the confident cell's own score and not "close to 1".
        expected = float(torch.sigmoid(torch.tensor(9.0)) * torch.sigmoid(torch.tensor(2.0)))
        baseline = float(torch.sigmoid(torch.tensor(3.0)) * torch.sigmoid(torch.tensor(2.0)))
        assert decoded["boxes"].shape[0] == 1
        assert decoded["scores"][0].item() == pytest.approx(expected, abs=1e-5)
        assert expected > baseline

    def test_suppression_runs_before_the_cap(self) -> None:
        """Capping first would spend the whole budget on duplicates of one object and
        drop genuine detections that scored lower."""
        outputs = _all_cells_on_one_box((0, 0, 56, 56), rows=16, cols=16)
        decoded = detection_decode(outputs, 14)
        assert decoded["boxes"].shape[0] < MAX_DETECTIONS
