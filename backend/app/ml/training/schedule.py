"""The learning-speed schedule, set once per round (doc 99).

Per round rather than per step: rounds are what the user sets and sees, and a head's
round is short enough that a finer curve would change nothing measurable.
"""

from __future__ import annotations

import math

import torch

#: Where the cosine curve ends, as a share of the learning rate. Not zero: the last
#: rounds still make small corrections instead of standing still.
FLOOR = 0.05


def lr_factor(epoch: int, total: int, warmup: int, schedule: str) -> float:
    """The share of the learning rate for round `epoch` (1-based) of `total`."""
    if warmup > 0 and epoch <= warmup:
        return epoch / warmup
    if schedule != "cosine":
        return 1.0
    span = total - warmup - 1
    if span <= 0:
        return 1.0
    progress = (epoch - warmup - 1) / span
    return FLOOR + (1.0 - FLOOR) * 0.5 * (1.0 + math.cos(math.pi * progress))


def apply_schedule(optimiser: torch.optim.Optimizer, base: list[float], factor: float) -> None:
    """Scale every parameter group from its own base rate, so a backbone's lower share
    (doc 55's tenth) stays a tenth while the rate ramps up or down."""
    for group, rate in zip(optimiser.param_groups, base, strict=True):
        group["lr"] = rate * factor


__all__ = ["FLOOR", "apply_schedule", "lr_factor"]
