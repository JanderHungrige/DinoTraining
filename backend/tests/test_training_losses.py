"""Tests for losses and detection target assignment.

Assignment is where detection quality is won or lost: the smallest-box-wins rule is
what stops a large box swallowing every cell of the small objects inside it.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.heads.registry import get_head_type
from app.ml.training.losses import (
    IGNORE_INDEX,
    assign_detection_targets,
    classification_loss,
    detection_loss,
    loss_for,
    segmentation_loss,
)


class TestLossRegistry:
    def test_every_trainable_head_has_a_loss(self) -> None:
        from app.ml.heads.registry import all_head_types

        for spec in all_head_types():
            if spec.trainable:
                assert loss_for(spec) is not None, spec.id

    def test_untrainable_head_raises_with_an_explanation(self) -> None:
        depth = get_head_type("linear-depth")
        assert depth is not None
        with pytest.raises(LookupError, match="not trainable"):
            loss_for(depth)


class TestAssignDetectionTargets:
    def test_cell_inside_a_box_is_positive(self) -> None:
        targets = assign_detection_targets(
            [(0, 0.0, 0.0, 100.0, 100.0)], [], grid=(4, 4), patch_size=10, num_classes=1
        )
        assert bool(targets["positive"][0, 0])
        assert int(targets["class_target"][0, 0]) == 0

    def test_cell_outside_every_box_is_background(self) -> None:
        targets = assign_detection_targets(
            [(0, 0.0, 0.0, 15.0, 15.0)], [], grid=(4, 4), patch_size=10, num_classes=1
        )
        assert not bool(targets["positive"][3, 3])
        assert int(targets["class_target"][3, 3]) == -1

    def test_smallest_box_wins_an_overlap(self) -> None:
        """Otherwise a large box swallows the small objects inside it, which never train."""
        big = (0, 0.0, 0.0, 100.0, 100.0)
        small = (1, 0.0, 0.0, 25.0, 25.0)
        targets = assign_detection_targets(
            [big, small], [], grid=(10, 10), patch_size=10, num_classes=2
        )
        assert int(targets["class_target"][0, 0]) == 1  # inside both → small wins
        assert int(targets["class_target"][9, 9]) == 0  # only inside big

    def test_ltrb_distances_are_from_the_cell_centre(self) -> None:
        targets = assign_detection_targets(
            [(0, 0.0, 0.0, 100.0, 100.0)], [], grid=(1, 1), patch_size=10, num_classes=1
        )
        left, top, right, bottom = targets["box_target"][:, 0, 0].tolist()
        assert (left, top) == pytest.approx((5.0, 5.0))
        assert (right, bottom) == pytest.approx((95.0, 95.0))

    def test_unclear_region_is_ignored_not_background(self) -> None:
        """Forcing it to background trains the model to suppress the ambiguous cases."""
        targets = assign_detection_targets(
            [], [(0.0, 0.0, 100.0, 100.0)], grid=(4, 4), patch_size=10, num_classes=1
        )
        assert int(targets["class_target"][0, 0]) == IGNORE_INDEX

    def test_a_positive_cell_beats_an_overlapping_ignore_region(self) -> None:
        targets = assign_detection_targets(
            [(0, 0.0, 0.0, 100.0, 100.0)],
            [(0.0, 0.0, 100.0, 100.0)],
            grid=(4, 4),
            patch_size=10,
            num_classes=1,
        )
        assert int(targets["class_target"][0, 0]) == 0

    def test_no_boxes_yields_all_background(self) -> None:
        targets = assign_detection_targets([], [], grid=(3, 3), patch_size=10, num_classes=1)
        assert not bool(targets["positive"].any())


class TestLosses:
    def test_classification_loss_is_finite_and_positive(self) -> None:
        loss = classification_loss(
            {"logits": torch.randn(4, 3)}, {"labels": torch.tensor([0, 1, 2, 1])}
        )
        assert torch.isfinite(loss) and float(loss) > 0

    def test_classification_loss_falls_when_confident_and_correct(self) -> None:
        confident = torch.tensor([[10.0, -10.0]])
        unsure = torch.tensor([[0.1, 0.0]])
        labels = torch.tensor([0])
        assert float(classification_loss({"logits": confident}, {"labels": labels})) < float(
            classification_loss({"logits": unsure}, {"labels": labels})
        )

    def test_segmentation_loss_upsamples_patch_logits_to_the_mask(self) -> None:
        """Upsampling logits rather than shrinking the mask keeps every pixel supervising."""
        loss = segmentation_loss(
            {"logits": torch.randn(1, 3, 4, 4)},
            {"mask": torch.zeros(1, 32, 32, dtype=torch.long)},
        )
        assert torch.isfinite(loss)

    def test_segmentation_loss_skips_ignored_pixels(self) -> None:
        mask = torch.full((1, 8, 8), IGNORE_INDEX, dtype=torch.long)
        mask[0, :4, :4] = 1
        loss = segmentation_loss({"logits": torch.randn(1, 3, 8, 8)}, {"mask": mask})
        assert torch.isfinite(loss)

    def test_segmentation_loss_is_zero_ish_when_perfect(self) -> None:
        logits = torch.full((1, 2, 4, 4), -10.0)
        logits[0, 1] = 10.0
        mask = torch.ones(1, 4, 4, dtype=torch.long)
        loss = segmentation_loss({"logits": logits}, {"mask": mask})
        assert float(loss) < 0.01

    def test_detection_loss_is_finite_with_positives(self) -> None:
        targets = assign_detection_targets(
            [(0, 0.0, 0.0, 40.0, 40.0)], [], grid=(4, 4), patch_size=10, num_classes=2
        )
        outputs = {
            "class_logits": torch.randn(1, 2, 4, 4),
            "box_ltrb": torch.rand(1, 4, 4, 4) + 1.0,
            "centerness": torch.randn(1, 1, 4, 4),
        }
        batched = {
            "class_target": targets["class_target"].unsqueeze(0),
            "box_target": targets["box_target"].unsqueeze(0),
            "positive": targets["positive"].unsqueeze(0),
        }
        assert torch.isfinite(detection_loss(outputs, batched))

    def test_detection_loss_handles_a_pure_background_image(self) -> None:
        """A background-only image is legitimate supervision, not an error."""
        targets = assign_detection_targets([], [], grid=(4, 4), patch_size=10, num_classes=2)
        outputs = {
            "class_logits": torch.randn(1, 2, 4, 4),
            "box_ltrb": torch.rand(1, 4, 4, 4) + 1.0,
            "centerness": torch.randn(1, 1, 4, 4),
        }
        batched = {
            "class_target": targets["class_target"].unsqueeze(0),
            "box_target": targets["box_target"].unsqueeze(0),
            "positive": targets["positive"].unsqueeze(0),
        }
        loss = detection_loss(outputs, batched)
        assert torch.isfinite(loss) and float(loss) > 0

    def test_detection_loss_backpropagates(self) -> None:
        targets = assign_detection_targets(
            [(0, 0.0, 0.0, 40.0, 40.0)], [], grid=(4, 4), patch_size=10, num_classes=2
        )
        logits = torch.randn(1, 2, 4, 4, requires_grad=True)
        outputs = {
            "class_logits": logits,
            "box_ltrb": torch.rand(1, 4, 4, 4, requires_grad=True) + 1.0,
            "centerness": torch.randn(1, 1, 4, 4, requires_grad=True),
        }
        batched = {
            "class_target": targets["class_target"].unsqueeze(0),
            "box_target": targets["box_target"].unsqueeze(0),
            "positive": targets["positive"].unsqueeze(0),
        }
        detection_loss(outputs, batched).backward()
        assert logits.grad is not None
