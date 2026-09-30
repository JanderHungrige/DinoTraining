"""The knobs doc 99 made honest: schedule, warm-up, pictures per step, adapter options."""

from __future__ import annotations

import random

import pytest
import torch

from app.finetune.adapter import FinetuneSettings
from app.ml.training.loop import run_epoch
from app.ml.training.schedule import apply_schedule, lr_factor


class TestLrFactor:
    def test_constant_without_warmup_is_always_one(self) -> None:
        assert [lr_factor(r, 5, 0, "constant") for r in range(1, 6)] == [1.0] * 5

    def test_warmup_ramps_linearly(self) -> None:
        assert [lr_factor(r, 10, 4, "constant") for r in (1, 2, 4, 5)] == [0.25, 0.5, 1.0, 1.0]

    def test_cosine_starts_full_and_ends_at_five_percent(self) -> None:
        assert lr_factor(1, 11, 0, "cosine") == pytest.approx(1.0)
        assert lr_factor(11, 11, 0, "cosine") == pytest.approx(0.05)
        values = [lr_factor(r, 11, 0, "cosine") for r in range(1, 12)]
        assert values == sorted(values, reverse=True)

    def test_cosine_after_warmup_starts_at_full_speed(self) -> None:
        assert lr_factor(3, 10, 2, "cosine") == pytest.approx(1.0)


class TestApplySchedule:
    def test_every_group_scales_and_keeps_its_share(self) -> None:
        """The backbone's lower rate (a tenth) must stay a tenth while warming up."""
        head, backbone = torch.nn.Linear(2, 2), torch.nn.Linear(2, 2)
        optimiser = torch.optim.AdamW(
            [
                {"params": head.parameters(), "lr": 1e-3},
                {"params": backbone.parameters(), "lr": 1e-4},
            ]
        )
        base = [g["lr"] for g in optimiser.param_groups]
        apply_schedule(optimiser, base, 0.5)
        assert [g["lr"] for g in optimiser.param_groups] == pytest.approx([5e-4, 5e-5])


class _Counting(torch.optim.SGD):
    steps = 0

    def step(self, closure=None):  # type: ignore[no-untyped-def]
        type(self).steps += 1
        return super().step(closure)


class TestPicturesPerStep:
    def _cache(self, n: int) -> list[tuple[torch.Tensor, dict[str, torch.Tensor]]]:
        return [(torch.randn(1, 4), {"labels": torch.tensor([i % 2])}) for i in range(n)]

    @pytest.mark.parametrize(("batch", "steps"), [(1, 6), (2, 3), (4, 2), (8, 1)])
    def test_one_correction_per_batch(self, batch: int, steps: int) -> None:
        head = torch.nn.Linear(4, 2)
        _Counting.steps = 0
        optimiser = _Counting(head.parameters(), lr=0.1)

        def loss(out: object, targets: dict[str, torch.Tensor]) -> torch.Tensor:
            return torch.nn.functional.cross_entropy(out, targets["labels"])  # type: ignore[arg-type]

        run_epoch(head, optimiser, loss, self._cache(6), tuple(range(6)), batch_size=batch)  # type: ignore[arg-type]
        assert _Counting.steps == steps


class TestAdaptersReadTheirOptions:
    def test_sam2_jitter_follows_the_option(self) -> None:
        from app.finetune.adapters.sam2 import _jittered

        box = (10.0, 10.0, 20.0, 20.0)
        assert _jittered(box, random.Random(0), 0.0) == [10.0, 10.0, 20.0, 20.0]
        moved = _jittered(box, random.Random(0), 0.5)
        assert moved != [10.0, 10.0, 20.0, 20.0]
        assert all(abs(a - b) <= 5.0 for a, b in zip(moved, box, strict=True))

    def test_sam3_loss_weights_follow_the_options(self) -> None:
        """With every weight but 'found or not' at zero, an empty phrase's loss is that
        term alone, scaled by its weight."""
        from types import SimpleNamespace

        from app.finetune.adapters.sam3_loss import LossWeights, phrase_loss

        out = SimpleNamespace(
            pred_logits=torch.zeros(1, 4),
            presence_logits=None,
            pred_masks=torch.zeros(1, 4, 8, 8),
            pred_boxes=torch.zeros(1, 4, 4),
        )
        one = phrase_loss(out, [], (8, 8), LossWeights(cls=1, l1=0, giou=0, mask=0, dice=0))
        three = phrase_loss(out, [], (8, 8), LossWeights(cls=3, l1=0, giou=0, mask=0, dice=0))
        assert float(three) == pytest.approx(3 * float(one))

    def test_weights_come_from_settings(self) -> None:
        from app.finetune.adapters.sam3_loss import LossWeights

        weights = LossWeights.from_settings(FinetuneSettings(options={"l1_weight": 7.0}))
        assert weights.l1 == 7.0 and weights.cls == 2.0
