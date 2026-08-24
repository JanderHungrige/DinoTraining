"""The task-generic training loop.

Nothing here branches on task: the loss and metric functions arrive from registries
keyed by head type, and targets are built by one dispatch that mirrors the head spec's
declared ``target_format``. Adding a head type never edits this file.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import torch
from PIL import Image
from torch import Tensor, nn

from app.ml.backbone import Backbone, BackboneFeatures, extract
from app.ml.heads.registry import HeadTypeSpec
from app.ml.preprocess import (
    GeometryTransform,
    PreprocessPlan,
    apply_geometry,
    to_pixel_values,
    transform_boxes,
)
from app.ml.training.losses import assign_detection_targets
from app.ml.training.samples import TrainingSample

logger = logging.getLogger(__name__)

LossFn = Callable[[dict[str, Tensor], dict[str, Tensor]], Tensor]

#: One cached image: its frozen features and its targets, already in the same frame.
CachedSample = tuple[BackboneFeatures, dict[str, Tensor]]


def load_image(path: str) -> Image.Image | None:
    """Open an image, or None if it cannot be read.

    A single unreadable file must not kill a run that took minutes to get here; it is
    logged and skipped.
    """
    try:
        with Image.open(path) as handle:
            return handle.convert("RGB")
    except (OSError, ValueError) as exc:
        logger.warning("Skipping unreadable image %s: %s", path, exc)
        return None


def build_targets(
    spec: HeadTypeSpec,
    sample: TrainingSample,
    transform: GeometryTransform,
    grid: tuple[int, int],
    patch_size: int,
    num_classes: int,
) -> dict[str, Tensor]:
    """Targets for one sample, moved into the transformed frame.

    Boxes go through the *same* GeometryTransform the image did — that pairing is the
    whole point of `10`, and re-deriving it here would reintroduce the silent-drop bug.
    """
    if spec.task == "classification":
        return {"labels": torch.tensor([sample.image_class or 0], dtype=torch.long)}

    raw = [(x, y, w, h) for _, x, y, w, h in sample.targets]
    moved, keep = transform_boxes(transform, raw)
    classes = [sample.targets[index][0] for index in keep]
    ignored, _ = transform_boxes(transform, list(sample.ignore_regions))

    targets = assign_detection_targets(
        [(cls, *box) for cls, box in zip(classes, moved, strict=True)],
        ignored,
        grid,
        patch_size,
        num_classes=num_classes,
    )
    targets["boxes"] = torch.tensor(moved, dtype=torch.float32).reshape(-1, 4)
    targets["classes"] = torch.tensor(classes, dtype=torch.long)
    return targets


def to_device(targets: dict[str, Tensor], device: str | torch.device) -> dict[str, Tensor]:
    """Move every target tensor onto the device the features live on.

    Targets are built with plain ``torch.tensor`` calls, which land on CPU, while
    features and the head sit on MPS or CUDA. Mixing them raises "Placeholder storage
    has not been allocated on MPS device" from inside the loss — a message that names
    neither the tensor nor the caller. Doing this once, where the pairing is created,
    is what keeps every loss free of device handling.
    """
    return {key: value.to(device) for key, value in targets.items()}


def precompute_cache(
    backbone: Backbone,
    plan: PreprocessPlan,
    spec: HeadTypeSpec,
    samples: list[TrainingSample],
    num_classes: int,
) -> list[CachedSample]:
    """One backbone pass over the dataset.

    The frozen backbone's payoff: a given image yields identical features every epoch,
    so one pass replaces `epochs` passes. Only valid when augmentation is off, which is
    why the caller gates on that rather than exposing it as a user setting.
    """
    cached: list[CachedSample] = []
    for sample in samples:
        image = load_image(sample.path)
        if image is None:
            continue
        resized, transform = apply_geometry(plan, image)
        features = extract(backbone, to_pixel_values(plan, [resized]))
        targets = build_targets(
            spec, sample, transform, features.grid, plan.patch_size, num_classes
        )
        cached.append((features, to_device(targets, features.cls.device)))
    return cached


def batched(targets: dict[str, Tensor]) -> dict[str, Tensor]:
    """Add the batch dimension the dense losses expect."""
    prepared = dict(targets)
    for key in ("class_target", "positive"):
        if key in prepared and prepared[key].dim() == 2:
            prepared[key] = prepared[key].unsqueeze(0)
    if "box_target" in prepared and prepared["box_target"].dim() == 3:
        prepared["box_target"] = prepared["box_target"].unsqueeze(0)
    return prepared


def run_epoch(
    head: nn.Module,
    optimiser: torch.optim.Optimizer,
    compute_loss: LossFn,
    cache: list[CachedSample],
    indices: tuple[int, ...],
) -> float:
    """One training pass. Returns mean loss."""
    head.train()
    total = 0.0
    for index in indices:
        features, targets = cache[index]
        loss = compute_loss(head(features), batched(targets))
        optimiser.zero_grad()
        # torch ships Tensor.backward untyped; this is the library boundary.
        loss.backward()  # type: ignore[no-untyped-call]
        optimiser.step()
        # detach before float(): the loss still carries a grad_fn here, and torch warns
        # that converting it to a scalar can behave unexpectedly.
        total += float(loss.detach())
    return total / len(indices) if indices else 0.0


def evaluate(
    head: nn.Module,
    compute_loss: LossFn,
    cache: list[CachedSample],
    indices: tuple[int, ...],
) -> tuple[float, list[dict[str, Tensor]], list[dict[str, Tensor]]]:
    """Validation pass. Returns mean loss plus outputs and targets for metrics."""
    head.eval()
    total = 0.0
    outputs: list[dict[str, Tensor]] = []
    targets: list[dict[str, Tensor]] = []
    with torch.no_grad():
        for index in indices:
            features, target = cache[index]
            prepared = batched(target)
            out = head(features)
            total += float(compute_loss(out, prepared))
            outputs.append(out)
            targets.append(prepared)
    return (total / len(indices) if indices else 0.0), outputs, targets


def is_better(candidate: float, best: float | None, mode: str) -> bool:
    """Best-model comparison, honouring the head spec's declared metric direction."""
    if best is None:
        return True
    return candidate > best if mode == "max" else candidate < best
