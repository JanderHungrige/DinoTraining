"""SAM 3 fine-tuning's matching and loss, without the weights (doc 96)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
import torch

from app.finetune.adapters import get_adapter
from app.finetune.adapters.sam3 import Sam3Adapter, matched_iou, phrase_loss


def square(x: int, y: int, size: int = 10, frame: int = 40) -> np.ndarray:
    mask = np.zeros((frame, frame), dtype=bool)
    mask[y : y + size, x : x + size] = True
    return mask


def test_missed_and_invented_objects_both_count_zero() -> None:
    truths = [square(0, 0), square(20, 20)]
    assert matched_iou([square(0, 0), square(20, 20)], truths) == (2.0, 2)
    assert matched_iou([square(0, 0)], truths) == (1.0, 2)  # one missed
    assert matched_iou([square(0, 0), square(20, 20), square(0, 25)], truths) == (
        2.0,
        3,
    )  # one invented
    assert matched_iou([], []) == (0.0, 0)


def outputs(match_first: bool) -> SimpleNamespace:
    """Four queries; the first predicts the true square (or its complement)."""
    target = torch.from_numpy(square(10, 10, 20).astype(np.float32))
    masks = torch.full((1, 4, 40, 40), -8.0)
    masks[0, 0] = (target * 16 - 8) if match_first else (8 - target * 16)
    boxes = torch.tensor([[[0.5, 0.5, 0.5, 0.5]] + [[0.1, 0.1, 0.05, 0.05]] * 3])
    logits = torch.tensor([[4.0, -4.0, -4.0, -4.0]])
    return SimpleNamespace(
        pred_masks=masks,
        pred_boxes=boxes,
        pred_logits=logits,
        presence_logits=torch.tensor([[4.0]]),
    )


def test_the_loss_rewards_the_query_that_found_the_object() -> None:
    truth = [square(10, 10, 20)]
    assert phrase_loss(outputs(True), truth, (40, 40)) < phrase_loss(
        outputs(False), truth, (40, 40)
    )


def test_a_picture_without_the_phrase_teaches_none_here() -> None:
    confident = outputs(True)
    quiet = outputs(True)
    quiet.pred_logits = torch.full((1, 4), -6.0)
    quiet.presence_logits = torch.tensor([[-6.0]])
    assert phrase_loss(quiet, [], (40, 40)) < phrase_loss(confident, [], (40, 40))


def test_sam3_has_its_adapter() -> None:
    adapter = get_adapter("sam3")
    assert isinstance(adapter, Sam3Adapter)
    assert (adapter.primary_metric, adapter.weights_kind) == ("miou", "sam3-decoders")
    with pytest.raises(LookupError):
        get_adapter("sam4")
