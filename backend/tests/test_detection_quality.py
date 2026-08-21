"""Centerness and GIoU — the two localisation signals (doc 43).

Both exist because of one measurement: the detectors trained in doc 31 scored mAP@50
0.59-0.75 but mAP@75 0.065-0.203. They *found* objects and *placed* them badly, and the
two things that should have punished bad placement were not doing so.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.training.losses import centerness_from_ltrb, detection_loss, giou_from_ltrb


class TestCenterness:
    def test_a_perfectly_centred_cell_scores_one(self) -> None:
        value = centerness_from_ltrb(torch.tensor([[5.0, 5.0, 5.0, 5.0]])).item()
        assert value == pytest.approx(1.0)

    def test_a_cell_at_the_edge_scores_near_zero(self) -> None:
        # l is tiny and r is large: the cell sits on the box's left edge.
        value = centerness_from_ltrb(torch.tensor([[0.01, 5.0, 10.0, 5.0]])).item()
        assert value < 0.05

    def test_it_falls_off_monotonically(self) -> None:
        """The whole point: a score that *ranks* placements. A flat or noisy signal would
        leave a badly-placed box ranking as highly as a good one, which is what the binary
        mask did."""
        centred = centerness_from_ltrb(torch.tensor([[5.0, 5.0, 5.0, 5.0]])).item()
        offset = centerness_from_ltrb(torch.tensor([[2.0, 5.0, 8.0, 5.0]])).item()
        far = centerness_from_ltrb(torch.tensor([[0.5, 5.0, 9.5, 5.0]])).item()
        assert centred > offset > far

    def test_it_is_not_the_positive_mask(self) -> None:
        # The regression this replaces: every positive cell used to get exactly 1.0, so
        # centerness carried no information the class head did not already have.
        values = centerness_from_ltrb(
            torch.tensor([[5.0, 5.0, 5.0, 5.0], [1.0, 5.0, 9.0, 5.0]])
        )
        assert not torch.allclose(values, torch.ones_like(values))

    def test_it_stays_in_range_for_a_degenerate_box(self) -> None:
        # A zero-width target would divide by zero without the clamp.
        value = centerness_from_ltrb(torch.tensor([[0.0, 5.0, 0.0, 5.0]])).item()
        assert 0.0 <= value <= 1.0


class TestGiou:
    def test_identical_boxes_score_one(self) -> None:
        box = torch.tensor([[4.0, 6.0, 4.0, 6.0]])
        assert giou_from_ltrb(box, box).item() == pytest.approx(1.0, abs=1e-4)

    def test_it_is_scale_invariant(self) -> None:
        """The reason it replaces L1. A 10% error scores the same on a small box and a
        large one; an L1 on pixel distances counted the large one as ten times worse."""
        small = giou_from_ltrb(
            torch.tensor([[11.0, 11.0, 11.0, 11.0]]), torch.tensor([[10.0, 10.0, 10.0, 10.0]])
        ).item()
        large = giou_from_ltrb(
            torch.tensor([[110.0, 110.0, 110.0, 110.0]]),
            torch.tensor([[100.0, 100.0, 100.0, 100.0]]),
        ).item()
        assert small == pytest.approx(large, abs=1e-4)

    def test_a_worse_box_scores_lower(self) -> None:
        target = torch.tensor([[10.0, 10.0, 10.0, 10.0]])
        close = giou_from_ltrb(torch.tensor([[11.0, 11.0, 11.0, 11.0]]), target).item()
        far = giou_from_ltrb(torch.tensor([[30.0, 30.0, 30.0, 30.0]]), target).item()
        assert close > far

    def test_it_stays_bounded(self) -> None:
        # Bounded in [-1, 1] is what removes the hand-tuned 0.05 scale the L1 term needed.
        wild = giou_from_ltrb(
            torch.tensor([[500.0, 0.1, 500.0, 0.1]]), torch.tensor([[1.0, 50.0, 1.0, 50.0]])
        ).item()
        assert -1.0 <= wild <= 1.0


class TestTheLossUsesThem:
    def _batch(self, predicted: list[float], actual: list[float]) -> tuple[dict, dict]:
        outputs = {
            "class_logits": torch.zeros(1, 2, 1, 1),
            "box_ltrb": torch.tensor(predicted).reshape(1, 4, 1, 1),
            "centerness": torch.zeros(1, 1, 1, 1),
        }
        targets = {
            "class_target": torch.zeros(1, 1, dtype=torch.long),
            "box_target": torch.tensor(actual).reshape(1, 4, 1, 1),
            "positive": torch.ones(1, 1, dtype=torch.bool),
            "num_classes": torch.tensor(2),
        }
        return outputs, targets

    def test_a_better_box_gives_a_lower_loss(self) -> None:
        good = detection_loss(*self._batch([9.0, 9.0, 9.0, 9.0], [10.0, 10.0, 10.0, 10.0]))
        bad = detection_loss(*self._batch([2.0, 2.0, 40.0, 40.0], [10.0, 10.0, 10.0, 10.0]))
        assert good.item() < bad.item()

    def test_a_pure_background_batch_still_returns_a_loss(self) -> None:
        outputs, targets = self._batch([5.0] * 4, [5.0] * 4)
        targets["positive"] = torch.zeros(1, 1, dtype=torch.bool)
        targets["class_target"] = torch.full((1, 1), -1, dtype=torch.long)
        assert torch.isfinite(detection_loss(outputs, targets))

    def test_the_loss_is_finite_and_differentiable(self) -> None:
        outputs, targets = self._batch([9.0, 9.0, 9.0, 9.0], [10.0, 10.0, 10.0, 10.0])
        outputs["box_ltrb"] = outputs["box_ltrb"].requires_grad_(True)
        loss = detection_loss(outputs, targets)
        loss.backward()
        assert torch.isfinite(loss)
        assert outputs["box_ltrb"].grad is not None
