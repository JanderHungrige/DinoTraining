"""Turning raw head outputs into consumable predictions, keyed by head type.

A registry alongside losses and metrics, for the same reason: no consumer branches on
task. Classification and segmentation read logits directly, so their entries are the
identity; detection needs its per-cell predictions decoded into boxes.

The decode happens here and only here — `decode_ltrb_to_boxes` owns the xywh convention,
so nothing downstream re-derives it.

**Lives under `heads/`, not `training/`.** It is keyed by head-type id and imports only
from `heads.*`. It began life in the training package when the loop was its only caller;
`16-inference-engine` is the second, and an inference module importing from `training`
would misdescribe the dependency.
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
    # --- non-trainable head types (added by doc 16) ------------------------------
    # These had no entry while the table lived under training/: the loop only ever
    # asks for trainable heads, so it was complete for that caller. Inference must
    # serve all seven, and the four below include every pretrained default — i.e.
    # exactly the heads Wave 3 nominates as its smoke test. All are identity:
    # classification and segmentation consumers read logits, and both depth heads
    # already emit metres from their own forward.
    "linear-depth": identity_decode,
    "dinov2-linear-classifier-in1k": identity_decode,
    "dinov2-linear-segmenter-ade20k": identity_decode,
    "dinov2-linear-depth-nyu": identity_decode,
}


def decode_for(spec: HeadTypeSpec) -> DecodeFn:
    """The decoder for a head type. Identity is a legitimate answer, not a gap."""
    decoder = DECODERS.get(spec.id)
    if decoder is None:
        raise LookupError(f"No decoder registered for {spec.id}")
    return decoder
