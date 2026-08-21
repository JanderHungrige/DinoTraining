"""Loss functions, keyed by head type.

A registry rather than an ``if task == ...`` in the loop: adding a head type adds an
entry here, and the training loop is never touched.
"""

from __future__ import annotations

from collections.abc import Callable

import torch
from torch import Tensor
from torch.nn import functional as torch_functional

from app.ml.heads.registry import HeadTypeSpec

#: (outputs, targets) -> scalar loss. ``targets`` is whatever the head type's assigner
#: produced; each loss knows its own target shape because both are keyed by head type.
LossFn = Callable[[dict[str, Tensor], dict[str, Tensor]], Tensor]

#: Mask value meaning "not annotated" — matches preprocess.DEFAULT_IGNORE_INDEX.
IGNORE_INDEX = 255


def classification_loss(
    outputs: dict[str, Tensor], targets: dict[str, Tensor]
) -> Tensor:
    """Cross-entropy over image-level class logits."""
    return torch_functional.cross_entropy(outputs["logits"], targets["labels"])


def segmentation_loss(outputs: dict[str, Tensor], targets: dict[str, Tensor]) -> Tensor:
    """Per-pixel cross-entropy against a label mask, skipping unannotated pixels.

    ``ignore_index`` is what makes letterbox padding harmless: padded regions carry 255
    and are excluded, rather than teaching the model that padding is background.
    """
    logits = outputs["logits"]
    mask = targets["mask"]
    if logits.shape[-2:] != mask.shape[-2:]:
        # Heads emit at patch resolution; the mask is at image resolution. Upsampling
        # logits (not downsampling the mask) keeps every annotated pixel supervising.
        logits = torch_functional.interpolate(
            logits, size=mask.shape[-2:], mode="bilinear", align_corners=False
        )
    return torch_functional.cross_entropy(logits, mask.long(), ignore_index=IGNORE_INDEX)


def assign_detection_targets(
    boxes: list[tuple[int, float, float, float, float]],
    ignore_regions: list[tuple[float, float, float, float]],
    grid: tuple[int, int],
    patch_size: int,
    num_classes: int,
) -> dict[str, Tensor]:
    """Centre-sampling assignment: a cell is positive if its centre falls in a box.

    When several boxes contain a cell, the **smallest** wins. Without that rule a large
    box swallows every cell of the small objects inside it, and the small objects are
    never learned — the classic ambiguity FCOS resolves by area.

    Returns per-cell class targets (``-1`` = background, ``IGNORE_INDEX`` = ignore),
    ltrb regression targets, and a positive mask.
    """
    rows, cols = grid
    class_target = torch.full((rows, cols), -1, dtype=torch.long)
    box_target = torch.zeros((4, rows, cols), dtype=torch.float32)
    positive = torch.zeros((rows, cols), dtype=torch.bool)
    best_area = torch.full((rows, cols), float("inf"))

    for row in range(rows):
        centre_y = (row + 0.5) * patch_size
        for col in range(cols):
            centre_x = (col + 0.5) * patch_size

            for class_index, x, y, w, h in boxes:
                if not (x <= centre_x <= x + w and y <= centre_y <= y + h):
                    continue
                area = w * h
                if area >= best_area[row, col]:
                    continue
                best_area[row, col] = area
                class_target[row, col] = class_index
                positive[row, col] = True
                box_target[:, row, col] = torch.tensor(
                    [centre_x - x, centre_y - y, x + w - centre_x, y + h - centre_y]
                )

            if positive[row, col]:
                continue
            # Only unmatched cells can be ignored: a cell that is a genuine positive
            # stays supervised even if an unclear box happens to overlap it.
            for x, y, w, h in ignore_regions:
                if x <= centre_x <= x + w and y <= centre_y <= y + h:
                    class_target[row, col] = IGNORE_INDEX
                    break

    return {
        "class_target": class_target,
        "box_target": box_target,
        "positive": positive,
        "num_classes": torch.tensor(num_classes),
    }


def centerness_from_ltrb(ltrb: Tensor) -> Tensor:
    """FCOS centerness for each cell, from its **ground-truth** ltrb distances.

    ``sqrt(min(l,r)/max(l,r) · min(t,b)/max(t,b))`` — 1 at a box's centre, falling to 0 at
    its edges. This is the localisation-quality signal `decode.py` multiplies into the
    score, and it is what makes a well-centred prediction outrank a badly-placed one.

    Until doc 43 the target was the *positive mask* — 1 inside any box, 0 outside — which
    is the same information the class head already carries. The score was therefore
    `class × (roughly class)`, with no term reflecting how well a box was placed. mAP@50
    barely noticed; mAP@75 collapsed, to 0.065 on chess.
    """
    left, top, right, bottom = ltrb.unbind(dim=-1)
    epsilon = 1e-6
    horizontal = torch.minimum(left, right) / torch.clamp(torch.maximum(left, right), min=epsilon)
    vertical = torch.minimum(top, bottom) / torch.clamp(torch.maximum(top, bottom), min=epsilon)
    return torch.sqrt(torch.clamp(horizontal * vertical, min=0.0))


def giou_from_ltrb(predicted: Tensor, target: Tensor) -> Tensor:
    """Generalised IoU between two boxes expressed as distances from the *same* centre.

    Both boxes share their cell centre, so GIoU needs no absolute coordinates: the widths
    are `l + r` and the overlaps are `min(l₁,l₂) + min(r₁,r₂)`.

    Replaces an L1 loss on pixel distances, which optimised something other than the metric
    being reported — a 5 px error counted the same on a 20 px object as on a 200 px one —
    and needed a hand-tuned `0.05` scale to stop it dominating two logit-scale terms. GIoU
    is scale-invariant and bounded in [-1, 1], so it needs no such fudge.
    """
    epsilon = 1e-7
    pl, pt, pr, pb = predicted.unbind(dim=-1)
    tl, tt, tr, tb = target.unbind(dim=-1)

    intersect = (torch.minimum(pl, tl) + torch.minimum(pr, tr)).clamp(min=0) * (
        torch.minimum(pt, tt) + torch.minimum(pb, tb)
    ).clamp(min=0)
    predicted_area = (pl + pr) * (pt + pb)
    target_area = (tl + tr) * (tt + tb)
    union = predicted_area + target_area - intersect

    enclosing = (torch.maximum(pl, tl) + torch.maximum(pr, tr)) * (
        torch.maximum(pt, tt) + torch.maximum(pb, tb)
    )
    iou = intersect / (union + epsilon)
    return iou - (enclosing - union) / (enclosing + epsilon)


def detection_loss(outputs: dict[str, Tensor], targets: dict[str, Tensor]) -> Tensor:
    """Classification + **GIoU** box regression + **continuous** centerness.

    Classification is computed over every non-ignored cell (background included, which
    is what teaches suppression); regression and centerness only over positives, since
    a background cell has no box to regress to and an untrained centerness there costs
    nothing — the class term already suppresses it.

    Two things changed in doc 43, both aimed at the mAP@75 collapse measured in doc 31:
    the centerness target became the real FCOS formula rather than the positive mask, and
    the box term became GIoU rather than a scaled L1. See the helpers above for why each
    was wrong.
    """
    class_logits = outputs["class_logits"]
    class_target = targets["class_target"]
    positive = targets["positive"]

    batch, num_classes, rows, cols = class_logits.shape
    flat_logits = class_logits.permute(0, 2, 3, 1).reshape(-1, num_classes)
    flat_target = class_target.reshape(-1)

    keep = flat_target != IGNORE_INDEX
    one_hot = torch.zeros_like(flat_logits)
    labelled = keep & (flat_target >= 0)
    if bool(labelled.any()):
        one_hot[labelled, flat_target[labelled]] = 1.0

    cls_loss = torch_functional.binary_cross_entropy_with_logits(
        flat_logits[keep], one_hot[keep], reduction="mean"
    )

    positive_count = int(positive.sum())
    if positive_count == 0:
        # A pure-background batch is legitimate supervision; there is simply nothing to
        # regress. Returning only the classification term keeps the graph connected.
        return cls_loss

    box_pred = outputs["box_ltrb"].permute(0, 2, 3, 1).reshape(-1, 4)
    box_true = targets["box_target"].permute(0, 2, 3, 1).reshape(-1, 4)
    positive_flat = positive.reshape(-1)

    predicted = box_pred[positive_flat]
    actual = box_true[positive_flat]
    quality = centerness_from_ltrb(actual)

    # Weighted by centerness, as FCOS does: a cell near a box's edge sees that box at a
    # glancing angle, and letting it pull the regression as hard as a central cell is what
    # blurs the extents everything else then has to rank.
    weight_sum = torch.clamp(quality.sum(), min=1e-6)
    box_loss = (((1.0 - giou_from_ltrb(predicted, actual)) * quality).sum()) / weight_sum

    centerness_loss = torch_functional.binary_cross_entropy_with_logits(
        outputs["centerness"].reshape(-1)[positive_flat], quality, reduction="mean"
    )

    # No scale fudge: GIoU is bounded in [-1, 1] and centerness BCE is a logit-scale term,
    # so the three sit on comparable footing without hand-tuning.
    return cls_loss + box_loss + centerness_loss


LOSSES: dict[str, LossFn] = {
    "linear-classifier": classification_loss,
    "dense-detector": detection_loss,
    "linear-segmenter": segmentation_loss,
}


def loss_for(spec: HeadTypeSpec) -> LossFn:
    """The loss for a head type. Raises for anything this app cannot train."""
    loss = LOSSES.get(spec.id)
    if loss is None:
        raise LookupError(
            f"No loss registered for {spec.id}"
            + ("" if spec.trainable else " — this head type is not trainable in this app")
        )
    return loss
