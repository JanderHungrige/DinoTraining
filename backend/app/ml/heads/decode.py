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
from torchvision.ops import batched_nms

from app.ml.heads.modules import decode_ltrb_to_boxes
from app.ml.heads.registry import HeadTypeSpec

#: (raw head outputs, patch_size) -> outputs shaped for the metric function.
DecodeFn = Callable[[dict[str, Tensor], int], dict[str, Tensor]]

#: Detections kept per image. Metrics only need enough to cover recall; keeping every
#: cell would make average_precision quadratic in grid size for no gain.
MAX_DETECTIONS = 100

#: Overlap above which two same-class boxes are treated as the same object.
#: 0.5 is the COCO convention and matches `map_50`, the metric this most affects.
NMS_IOU_THRESHOLD = 0.5


def identity_decode(outputs: dict[str, Tensor], patch_size: int) -> dict[str, Tensor]:
    """Classification and segmentation metrics read logits directly."""
    return outputs


def _suppress_overlaps(boxes: Tensor, scores: Tensor, classes: Tensor) -> Tensor:
    """Class-aware NMS. Returns surviving indices, already ordered by descending score.

    Every patch cell whose receptive field covers an object regresses its *own* box to
    that object, so one dog becomes thirty near-identical boxes. Centerness damps the
    worst of them but suppresses nothing: it reweights, and a weighted duplicate is still
    a duplicate. Without this step a single thermal image returned 32 overlapping
    `person` boxes, and every one past the first counts as a false positive — so this
    depressed `map` as much as it cluttered the review UI.

    Class-aware (``batched_nms``) rather than global: a dog standing in front of a person
    legitimately overlaps, and suppressing across classes would delete the rarer one.
    """
    if scores.numel() == 0:
        return torch.empty(0, dtype=torch.long, device=scores.device)
    # torchvision wants corners; the rest of this project speaks xywh.
    x_min, y_min, width, height = boxes.unbind(dim=-1)
    corners = torch.stack([x_min, y_min, x_min + width, y_min + height], dim=-1)
    # torchvision ships no stubs for ops, so the return is Any without this.
    keep: Tensor = batched_nms(corners, scores, classes, NMS_IOU_THRESHOLD)
    return keep


def detection_decode(outputs: dict[str, Tensor], patch_size: int) -> dict[str, Tensor]:
    """Per-cell predictions to ranked, de-duplicated boxes.

    Score is ``sigmoid(class) * sigmoid(centerness)``: centerness suppresses cells near a
    box edge, which otherwise produce confident but badly-placed boxes and depress AP.
    Overlapping duplicates are then removed by NMS — the head type has always advertised
    it, and until doc 31 exercised a trained detector on real images, nothing implemented
    it.
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

    # NMS before the cap, not after: taking the top 100 cells first would fill the budget
    # with duplicates of the same object and drop genuine second detections.
    survivors = _suppress_overlaps(boxes, scores, classes)[:MAX_DETECTIONS]
    return {
        "boxes": boxes[survivors],
        "scores": scores[survivors],
        "classes": classes[survivors],
    }


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
