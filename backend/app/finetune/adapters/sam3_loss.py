"""SAM 3's training loss: a Hungarian match of queries to one phrase's objects (doc 96).

Split from the adapter so the weights can be settings (doc 99): score, box L1, box GIoU,
mask focal and mask dice default to DETR's 2, 5, 2, 5, 5.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from scipy.optimize import linear_sum_assignment
from torch.nn import functional as F
from torchvision.ops import generalized_box_iou

from app.finetune.adapter import FinetuneSettings, param

FAMILY = "sam3"


@dataclass(frozen=True)
class LossWeights:
    cls: float = 2.0
    l1: float = 5.0
    giou: float = 2.0
    mask: float = 5.0
    dice: float = 5.0

    @classmethod
    def from_settings(cls, settings: FinetuneSettings) -> LossWeights:
        return cls(
            cls=param(settings, FAMILY, "class_weight"),
            l1=param(settings, FAMILY, "l1_weight"),
            giou=param(settings, FAMILY, "giou_weight"),
            mask=param(settings, FAMILY, "mask_weight"),
            dice=param(settings, FAMILY, "dice_weight"),
        )


def _boxes(masks: list[np.ndarray], size: tuple[int, int]) -> torch.Tensor:
    """Normalised (cx, cy, w, h) boxes of masks, SAM 3's box format."""
    h, w = size
    rows = []
    for mask in masks:
        ys, xs = np.nonzero(mask)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        rows.append([(x0 + x1) / 2 / w, (y0 + y1) / 2 / h, (x1 - x0) / w, (y1 - y0) / h])
    return torch.tensor(rows, dtype=torch.float32)


def _xyxy(boxes: torch.Tensor) -> torch.Tensor:
    cx, cy, w, h = boxes.unbind(-1)
    return torch.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], -1)


def _focal(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    prob = logits.sigmoid()
    bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    p_t = prob * target + (1 - prob) * (1 - target)
    return (0.25 * (1 - p_t) ** 2 * bce).mean()


def _dice(prob: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    inter = prob.flatten(1) @ target.flatten(1).T
    return 1 - (2 * inter + 1) / (
        prob.flatten(1).sum(1)[:, None] + target.flatten(1).sum(1)[None] + 1
    )


def phrase_loss(
    out: Any,
    masks: list[np.ndarray],
    size: tuple[int, int],
    weights: LossWeights = LossWeights(),  # noqa: B008 - frozen, so a shared default is safe
) -> torch.Tensor:
    """Match the queries to one phrase's objects, and the loss on that match."""
    w = weights
    logits = out.pred_logits[0].reshape(-1)
    presence = out.presence_logits.reshape(-1)[:1] if out.presence_logits is not None else None

    def presence_loss(value: float) -> torch.Tensor:
        if presence is None:
            return torch.zeros((), device=logits.device)
        return F.binary_cross_entropy_with_logits(presence, torch.full_like(presence, value))

    if not masks:
        return w.cls * _focal(logits, torch.zeros_like(logits)) + presence_loss(0.0)
    pred_masks = out.pred_masks[0]
    target = torch.from_numpy(np.stack(masks).astype(np.float32))[:, None]
    target = F.interpolate(target, size=pred_masks.shape[-2:], mode="nearest")[:, 0].to(
        logits.device
    )
    true_boxes = _boxes(masks, size).to(logits.device)
    pred_boxes = out.pred_boxes[0]
    with torch.no_grad():
        cost = (
            w.dice * _dice(pred_masks.sigmoid(), target)
            + w.l1 * torch.cdist(pred_boxes, true_boxes, p=1)
            - w.cls * logits.sigmoid()[:, None]
        )
    rows, cols = linear_sum_assignment(cost.cpu().numpy())
    rows_t, cols_t = (
        torch.as_tensor(rows, device=logits.device),
        torch.as_tensor(cols, device=logits.device),
    )
    matched = torch.zeros_like(logits)
    matched[rows_t] = 1
    giou = torch.diag(generalized_box_iou(_xyxy(pred_boxes[rows_t]), _xyxy(true_boxes[cols_t])))
    return (
        w.cls * _focal(logits, matched)
        + presence_loss(1.0)
        + w.l1 * F.l1_loss(pred_boxes[rows_t], true_boxes[cols_t])
        + w.giou * (1 - giou).mean()
        + w.mask * _focal(pred_masks[rows_t], target[cols_t])
        + w.dice * torch.diag(_dice(pred_masks[rows_t].sigmoid(), target[cols_t])).mean()
    )


def matched_iou(predicted: list[np.ndarray], truths: list[np.ndarray]) -> tuple[float, int]:
    """(sum of IoUs of one-to-one matched pairs, number of objects counted)."""
    count = max(len(predicted), len(truths))
    if count == 0:
        return 0.0, 0
    if not predicted or not truths:
        return 0.0, count
    ious = np.array(
        [
            [np.logical_and(p, t).sum() / max(1, np.logical_or(p, t).sum()) for t in truths]
            for p in predicted
        ]
    )
    rows, cols = linear_sum_assignment(-ious)
    return float(ious[rows, cols].sum()), count


__all__ = ["LossWeights", "matched_iou", "phrase_loss"]
