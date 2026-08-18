"""Tests for the output decoders.

This registry exists because integration testing found metrics being handed raw
per-cell logits when they expected decoded boxes — the unit tests had fed the metric
function pre-decoded fixtures, so nothing caught the missing step.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.heads.decode import DECODERS, MAX_DETECTIONS, decode_for, detection_decode
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

    def test_one_entry_per_cell_when_under_the_cap(self) -> None:
        decoded = detection_decode(detector_outputs(rows=4, cols=4), 14)
        assert decoded["boxes"].shape == (16, 4)
        assert decoded["scores"].shape == (16,)
        assert decoded["classes"].shape == (16,)

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
