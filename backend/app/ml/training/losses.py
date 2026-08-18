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


def detection_loss(outputs: dict[str, Tensor], targets: dict[str, Tensor]) -> Tensor:
    """Focal-style classification + L1 box regression + centerness BCE.

    Classification is computed over every non-ignored cell (background included, which
    is what teaches suppression); regression and centerness only over positives, since
    a background cell has no box to regress to.
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

    box_loss = torch_functional.l1_loss(
        box_pred[positive_flat], box_true[positive_flat], reduction="mean"
    )

    centerness = outputs["centerness"].reshape(-1)
    centerness_target = positive_flat.float()
    centerness_loss = torch_functional.binary_cross_entropy_with_logits(
        centerness, centerness_target, reduction="mean"
    )

    # Box loss is scaled down: ltrb distances are in pixels and would otherwise dominate
    # two terms that live on a logit scale.
    return cls_loss + 0.05 * box_loss + centerness_loss


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
