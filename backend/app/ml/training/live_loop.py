"""Training with the backbone in the graph (doc 55).

The sibling of `loop.py`'s cached path, and deliberately shaped like it so the runner can
choose between them without either knowing about the other.

**Why it cannot be a flag on the cached loop.** That loop's whole structure is "features
were computed once, iterate over them". Here the image has to be decoded, preprocessed and
pushed through the backbone on *every* step, because the backbone's weights changed since
the last one. There is no cache to make optional — there is a different loop.

The cost is exactly what it sounds like: a run that took seconds takes minutes, because it
is now doing `epochs` backbone passes instead of one. That is the trade the user opted into
by unfreezing, and the UI says so before they start.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

import torch
from torch import nn

# `load_image` from `loop`, not a second copy: one definition of "an unreadable
# image is skipped, not fatal" is what keeps the two loops behaving alike.
from app.ml.augment import Preset
from app.ml.backbone import Backbone, extract_trainable
from app.ml.heads.registry import HeadTypeSpec
from app.ml.preprocess import PreprocessPlan, apply_geometry, to_pixel_values
from app.ml.training.augmented import augment_sample
from app.ml.training.loop import (
    LossFn,
    batched,
    build_targets,
    load_sample_image,
    to_device,
)
from app.ml.training.samples import TrainingSample

logger = logging.getLogger(__name__)

#: Gradients are clipped for the reason doc 44 clips them: a head fitted from scratch
#: produces large early losses, and one bad step through an unfrozen ViT undoes the
#: pretraining that made it worth using.
GRAD_CLIP = 1.0


@dataclass(frozen=True, slots=True)
class LivePass:
    """Everything one uncached pass needs, gathered once rather than threaded separately."""

    backbone: Backbone
    plan: PreprocessPlan
    spec: HeadTypeSpec
    samples: list[TrainingSample]
    num_classes: int
    #: Doc 87: each training image is changed as it loads. Never set for evaluation.
    augmentation: Preset | None = None


def forward_one(
    live: LivePass,
    head: nn.Module,
    sample: TrainingSample,
    rng: random.Random | None = None,
) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]] | None:
    """One image through backbone and head. None when the image will not open.

    Targets are built against the features' **own** grid, exactly as the cached path does —
    deriving the grid separately is how the two loops would drift into disagreeing about
    where a box belongs.
    """
    image = load_sample_image(sample)
    if image is None:
        return None
    if rng is not None and live.augmentation is not None:
        image, sample = augment_sample(image, sample, live.augmentation, rng)
    resized, transform = apply_geometry(live.plan, image)
    features = extract_trainable(live.backbone, to_pixel_values(live.plan, [resized]))
    targets = build_targets(
        live.spec, sample, transform, features.grid, live.plan.patch_size, live.num_classes
    )
    return head(features), batched(to_device(targets, features.cls.device))


def run_live_epoch(
    live: LivePass,
    head: nn.Module,
    optimiser: torch.optim.Optimizer,
    compute_loss: LossFn,
    indices: tuple[int, ...],
    rng: random.Random | None = None,
    batch_size: int = 1,
) -> float:
    """One training pass with the backbone training too. Returns mean loss.

    `batch_size` pictures per correction, by gradient accumulation (doc 99).
    """
    head.train()
    live.backbone.model.train()
    total = 0.0
    counted = 0
    pending = 0
    optimiser.zero_grad()

    for index in indices:
        pair = forward_one(live, head, live.samples[index], rng)
        if pair is None:
            continue
        output, targets = pair
        loss = compute_loss(output, targets)
        (loss / batch_size).backward()  # type: ignore[no-untyped-call]
        pending += 1
        if pending == batch_size:
            _step(optimiser)
            pending = 0

        total += float(loss.detach())
        counted += 1

    if pending:
        _step(optimiser)
    return total / counted if counted else 0.0


def _step(optimiser: torch.optim.Optimizer) -> None:
    # Both sets of parameters, not just the head's: the whole point here is that the
    # backbone is receiving gradients, and it is the one that cannot survive a spike.
    for group in optimiser.param_groups:
        torch.nn.utils.clip_grad_norm_(group["params"], GRAD_CLIP)
    optimiser.step()
    optimiser.zero_grad()


def evaluate_live(
    live: LivePass,
    head: nn.Module,
    compute_loss: LossFn,
    indices: tuple[int, ...],
) -> tuple[float, list[dict[str, torch.Tensor]], list[dict[str, torch.Tensor]]]:
    """Validation with the current backbone weights. Mirrors `loop.evaluate`'s return."""
    head.eval()
    live.backbone.model.eval()
    total = 0.0
    counted = 0
    outputs: list[dict[str, torch.Tensor]] = []
    targets: list[dict[str, torch.Tensor]] = []

    with torch.no_grad():
        for index in indices:
            pair = forward_one(live, head, live.samples[index])
            if pair is None:
                continue
            output, target = pair
            total += float(compute_loss(output, target))
            outputs.append(output)
            targets.append(target)
            counted += 1

    return (total / counted if counted else 0.0), outputs, targets


__all__ = ["GRAD_CLIP", "LivePass", "evaluate_live", "forward_one", "run_live_epoch"]
