"""Tests for metric computation.

Metric names must match what each head spec declares, since the stream in `13` reads
keys rather than hardcoding them — a rename here silently empties the UI charts.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.heads.registry import all_head_types, get_head_type
from app.ml.training.losses import IGNORE_INDEX
from app.ml.training.metrics import (
    average_precision,
    classification_metrics,
    detection_metrics,
    metrics_for,
    segmentation_metrics,
)


class TestMetricRegistry:
    def test_metric_keys_match_the_declared_spec_names(self) -> None:
        """The registry declares metric names; the computation must produce those keys."""
        spec = get_head_type("linear-classifier")
        assert spec is not None
        produced = classification_metrics(
            [{"logits": torch.tensor([[2.0, 0.0]])}], [{"labels": torch.tensor([0])}]
        )
        assert set(spec.metrics) == set(produced)

    def test_segmentation_keys_match_the_spec(self) -> None:
        spec = get_head_type("linear-segmenter")
        assert spec is not None
        produced = segmentation_metrics(
            [{"logits": torch.randn(1, 2, 4, 4)}],
            [{"mask": torch.zeros(1, 4, 4, dtype=torch.long)}],
        )
        assert set(spec.metrics) == set(produced)

    def test_every_trainable_head_has_metrics(self) -> None:
        for spec in all_head_types():
            if spec.trainable:
                assert metrics_for(spec) is not None, spec.id

    def test_primary_metric_is_actually_produced(self) -> None:
        """08 requires primary_metric ∈ metrics; this checks the computation agrees."""
        spec = get_head_type("dense-detector")
        assert spec is not None
        produced = detection_metrics(
            [{"boxes": torch.zeros(0, 4), "scores": torch.zeros(0), "classes": torch.zeros(0)}],
            [{"boxes": torch.zeros(0, 4), "classes": torch.zeros(0)}],
        )
        assert spec.primary_metric in produced


class TestClassificationMetrics:
    def test_perfect_predictions_score_one(self) -> None:
        out = [{"logits": torch.tensor([[5.0, 0.0], [0.0, 5.0]])}]
        tgt = [{"labels": torch.tensor([0, 1])}]
        result = classification_metrics(out, tgt)
        assert result["accuracy"] == pytest.approx(1.0)
        assert result["macro_f1"] == pytest.approx(1.0)

    def test_all_wrong_scores_zero(self) -> None:
        out = [{"logits": torch.tensor([[0.0, 5.0], [5.0, 0.0]])}]
        tgt = [{"labels": torch.tensor([0, 1])}]
        assert classification_metrics(out, tgt)["accuracy"] == pytest.approx(0.0)

    def test_macro_f1_punishes_ignoring_a_rare_class(self) -> None:
        """Accuracy alone would hide this on the imbalanced datasets humans produce."""
        # 9 of class 0, 1 of class 1; model always predicts 0.
        logits = torch.tensor([[5.0, 0.0]] * 10)
        labels = torch.tensor([0] * 9 + [1])
        result = classification_metrics([{"logits": logits}], [{"labels": labels}])
        assert result["accuracy"] == pytest.approx(0.9)
        assert result["macro_f1"] < 0.6

    def test_empty_input_is_zero_not_a_crash(self) -> None:
        assert classification_metrics([], []) == {"accuracy": 0.0, "macro_f1": 0.0}


class TestSegmentationMetrics:
    def test_perfect_mask_scores_one(self) -> None:
        logits = torch.full((1, 2, 4, 4), -10.0)
        logits[0, 1] = 10.0
        result = segmentation_metrics(
            [{"logits": logits}], [{"mask": torch.ones(1, 4, 4, dtype=torch.long)}]
        )
        assert result["miou"] == pytest.approx(1.0)
        assert result["pixel_accuracy"] == pytest.approx(1.0)

    def test_ignored_pixels_do_not_inflate_accuracy(self) -> None:
        """Counting letterbox padding as correct background makes the number meaningless."""
        mask = torch.full((1, 4, 4), IGNORE_INDEX, dtype=torch.long)
        mask[0, 0, 0] = 1
        logits = torch.full((1, 2, 4, 4), -10.0)
        logits[0, 0] = 10.0  # predicts class 0 everywhere; the one real pixel is class 1
        result = segmentation_metrics([{"logits": logits}], [{"mask": mask}])
        assert result["pixel_accuracy"] == pytest.approx(0.0)

    def test_empty_input_is_zero(self) -> None:
        assert segmentation_metrics([], []) == {"miou": 0.0, "pixel_accuracy": 0.0}


class TestAveragePrecision:
    def test_perfect_detection_scores_one(self) -> None:
        gt = [((0.0, 0.0, 10.0, 10.0), 0)]
        pred = [(0.9, (0.0, 0.0, 10.0, 10.0), 0)]
        assert average_precision(pred, gt, 0.5) == pytest.approx(1.0)

    def test_no_overlap_scores_zero(self) -> None:
        gt = [((0.0, 0.0, 10.0, 10.0), 0)]
        pred = [(0.9, (100.0, 100.0, 10.0, 10.0), 0)]
        assert average_precision(pred, gt, 0.5) == pytest.approx(0.0)

    def test_duplicate_detections_lower_precision(self) -> None:
        """Each ground-truth box may be matched once; a second hit on it is a false
        positive. Without that rule, spraying the same box repeatedly would score
        perfectly. The duplicate must sit between two true positives to be visible —
        recall has to still be climbing for the precision drop to enter the integral."""
        gt = [((0.0, 0.0, 10.0, 10.0), 0), ((100.0, 100.0, 10.0, 10.0), 0)]
        clean = [(0.9, (0.0, 0.0, 10.0, 10.0), 0), (0.7, (100.0, 100.0, 10.0, 10.0), 0)]
        duplicated = [
            (0.9, (0.0, 0.0, 10.0, 10.0), 0),
            (0.8, (0.0, 0.0, 10.0, 10.0), 0),  # same object again → false positive
            (0.7, (100.0, 100.0, 10.0, 10.0), 0),
        ]
        assert average_precision(clean, gt, 0.5) == pytest.approx(1.0)
        assert average_precision(duplicated, gt, 0.5) < 0.9

    def test_wrong_class_does_not_match(self) -> None:
        gt = [((0.0, 0.0, 10.0, 10.0), 0)]
        pred = [(0.9, (0.0, 0.0, 10.0, 10.0), 1)]
        assert average_precision(pred, gt, 0.5) == pytest.approx(0.0)

    def test_stricter_threshold_rejects_a_loose_box(self) -> None:
        """Offset 1 gives IoU 0.68 — comfortably over 0.5, clearly under 0.9."""
        gt = [((0.0, 0.0, 10.0, 10.0), 0)]
        pred = [(0.9, (1.0, 1.0, 10.0, 10.0), 0)]
        assert average_precision(pred, gt, 0.5) == pytest.approx(1.0)
        assert average_precision(pred, gt, 0.9) == pytest.approx(0.0)

    def test_empty_everything_is_zero(self) -> None:
        assert average_precision([], [], 0.5) == 0.0


class TestDetectionMetrics:
    def test_produces_all_three_declared_keys(self) -> None:
        out = [
            {
                "boxes": torch.tensor([[0.0, 0.0, 10.0, 10.0]]),
                "scores": torch.tensor([0.9]),
                "classes": torch.tensor([0]),
            }
        ]
        tgt = [{"boxes": torch.tensor([[0.0, 0.0, 10.0, 10.0]]), "classes": torch.tensor([0])}]
        result = detection_metrics(out, tgt)
        assert set(result) == {"map", "map_50", "map_75"}
        assert result["map_50"] == pytest.approx(1.0)
