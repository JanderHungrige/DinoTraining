"""SAM 2 fine-tuning's pieces that do not need the weights (doc 94)."""

from __future__ import annotations

import random

import numpy as np
import pytest
import torch

from app.finetune.adapters import get_adapter
from app.finetune.adapters.sam2 import Sam2Adapter, _box, _jittered, _loss, _scaled

JITTER = 0.1  # the catalogue's default box looseness (doc 99)


def test_the_prompt_box_is_the_mask_s_own_extent() -> None:
    mask = np.zeros((40, 60), dtype=bool)
    mask[10:20, 5:35] = True
    assert _box(mask) == (5.0, 10.0, 35.0, 20.0)
    assert _box(np.zeros((4, 4), dtype=bool)) is None


def test_jitter_stays_within_a_tenth_of_the_box() -> None:
    rng = random.Random(0)
    for _ in range(50):
        x0, y0, x1, y1 = _jittered((100.0, 50.0, 200.0, 150.0), rng, JITTER)
        assert abs(x0 - 100) <= JITTER * 100 and abs(y1 - 150) <= JITTER * 100


def test_boxes_are_stretched_to_1024_like_the_processor() -> None:
    # A 2048x512 picture: x halves, y doubles (doc 85's "stretch").
    scaled = _scaled([[1024.0, 256.0, 2048.0, 512.0]], (512, 2048))
    assert scaled.tolist() == [[512.0, 512.0, 1024.0, 1024.0]]


def test_the_loss_rewards_the_right_mask_and_an_honest_iou() -> None:
    target = torch.zeros(1, 8, 8)
    target[0, 2:6, 2:6] = 1
    right = (target * 20 - 10).clone()
    wrong = -right
    honest = _loss(right, torch.tensor([1.0]), target)
    boastful = _loss(wrong, torch.tensor([1.0]), target)
    assert honest < boastful
    # The IoU head is taught the IoU the mask achieved: claiming 1.0 for a wrong mask costs.
    assert _loss(wrong, torch.tensor([0.0]), target) < boastful


def test_sam2_has_an_adapter_and_saves_only_its_decoder() -> None:
    adapter = get_adapter("sam2.1-hiera-small")
    assert isinstance(adapter, Sam2Adapter)
    assert (adapter.primary_metric, adapter.weights_kind) == ("miou", "sam-mask-decoder")
    with pytest.raises(LookupError):
        get_adapter("no-such-model")
