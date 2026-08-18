"""Turning raw head outputs into what metrics consume, keyed by head type.

A third registry alongside losses and metrics, for the same reason: the loop must not
branch on task. Classification and segmentation metrics read logits directly, so their
entries are the identity; detection needs its per-cell predictions decoded into boxes.

The decode happens here and only here — `decode_ltrb_to_boxes` owns the xywh convention,
so nothing downstream re-derives it.
"""

from __future__ import annotations

from collections.abc import Callable

import torch
from torch import Tensor

from app.ml.heads.modules import decode_ltrb_to_boxes
from app.ml.heads.registry import HeadTypeSpec

#: (raw head outputs, patch_size) -> outputs shaped for the metric function.
DecodeFn = Callable[[dict[str, Tensor], int], dict[str, Tensor]]

#: Detections kept per image. Metrics only need enough to cover recall; keeping every
#: cell would make average_precision quadratic in grid size for no gain.
MAX_DETECTIONS = 100


def identity_decode(outputs: dict[str, Tensor], patch_size: int) -> dict[str, Tensor]:
    """Classification and segmentation metrics read logits directly."""
    return outputs


def detection_decode(outputs: dict[str, Tensor], patch_size: int) -> dict[str, Tensor]:
    """Per-cell predictions to ranked boxes.

    Score is ``sigmoid(class) * sigmoid(centerness)``: centerness suppresses cells near a
    box edge, which otherwise produce confident but badly-placed boxes and depress AP.
    """
    class_logits = outputs["class_logits"]
    centerness = outputs["centerness"]
    grid = (int(class_logits.shape[-2]), int(class_logits.shape[-1]))

    boxes = decode_ltrb_to_boxes(outputs["box_ltrb"], grid, patch_size)[0]

    probabilities = torch.sigmoid(class_logits[0])
    best_score, best_class = probabilities.max(dim=0)
    centre = torch.sigmoid(centerness[0, 0])
    scores = (best_score * centre).reshape(-1)
    classes = best_class.reshape(-1)

    keep = min(MAX_DETECTIONS, scores.numel())
    top = torch.topk(scores, keep).indices
    return {"boxes": boxes[top], "scores": scores[top], "classes": classes[top]}


DECODERS: dict[str, DecodeFn] = {
    "linear-classifier": identity_decode,
    "dense-detector": detection_decode,
    "linear-segmenter": identity_decode,
}


def decode_for(spec: HeadTypeSpec) -> DecodeFn:
    """The decoder for a head type. Identity is a legitimate answer, not a gap."""
    decoder = DECODERS.get(spec.id)
    if decoder is None:
        raise LookupError(f"No decoder registered for {spec.id}")
    return decoder
