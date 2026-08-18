"""The four built-in head modules.

Every head takes :class:`BackboneFeatures` and returns ``dict[str, Tensor]``. The
uniform signature is deliberate: it is what lets the training job runner stay generic
instead of branching on task. Each head reads ``cls`` or ``patches`` itself, so that
dispatch lives here rather than in the trainer.

Heads output at *patch* resolution. Upsampling needs a target size the head does not
know, so :func:`upsample_logits` is called by the loss and the renderer explicitly.
"""

from __future__ import annotations

import torch
from torch import Tensor, nn

from app.ml.backbone import BackboneFeatures


class ClassificationHead(nn.Module):
    """Linear probe on the pooled CLS token."""

    def __init__(self, embed_dim: int, num_classes: int) -> None:
        super().__init__()
        self.linear = nn.Linear(embed_dim, num_classes)

    def forward(self, features: BackboneFeatures) -> dict[str, Tensor]:
        return {"logits": self.linear(features.cls)}


class DetectionHead(nn.Module):
    """Anchor-free FCOS-style head over the patch grid.

    Each cell predicts class logits, four distances to the box edges (l, t, r, b) and
    a centerness score. Distances go through ``softplus`` and are scaled by the patch
    size: a raw linear output would allow negative extents, which decode into inverted
    boxes that are hard to trace back to their cause.
    """

    def __init__(self, embed_dim: int, num_classes: int, patch_size: int = 14) -> None:
        super().__init__()
        self.patch_size = patch_size
        self.classifier = nn.Conv2d(embed_dim, num_classes, kernel_size=1)
        self.box_regressor = nn.Conv2d(embed_dim, 4, kernel_size=1)
        self.centerness = nn.Conv2d(embed_dim, 1, kernel_size=1)

    def forward(self, features: BackboneFeatures) -> dict[str, Tensor]:
        patches = features.patches
        raw_boxes = self.box_regressor(patches)
        return {
            "class_logits": self.classifier(patches),
            # softplus keeps distances strictly positive; the scale puts them in pixels.
            "box_ltrb": nn.functional.softplus(raw_boxes) * self.patch_size,
            "centerness": self.centerness(patches),
        }


class SegmentationHead(nn.Module):
    """Per-patch classification, upsampled to a mask by the caller."""

    def __init__(self, embed_dim: int, num_classes: int) -> None:
        super().__init__()
        self.classifier = nn.Conv2d(embed_dim, num_classes, kernel_size=1)

    def forward(self, features: BackboneFeatures) -> dict[str, Tensor]:
        return {"logits": self.classifier(features.patches)}


class DepthHead(nn.Module):
    """Single-channel monocular depth from patch features.

    Buildable but not fine-tunable in this app — "not trainable" is about the absence
    of depth ground truth here, not about whether the module can exist.
    """

    def __init__(self, embed_dim: int) -> None:
        super().__init__()
        self.regressor = nn.Conv2d(embed_dim, 1, kernel_size=1)

    def forward(self, features: BackboneFeatures) -> dict[str, Tensor]:
        # softplus: depth is a positive distance, and an unconstrained output would let
        # the model emit negative depths that no downstream renderer can interpret.
        return {"depth": nn.functional.softplus(self.regressor(features.patches))}


def upsample_logits(logits: Tensor, size: tuple[int, int]) -> Tensor:
    """Bilinearly resize ``(B, C, Gh, Gw)`` logits to an image-resolution ``(H, W)``.

    Kept out of the heads because the target size comes from the input image, which a
    head never sees.
    """
    resized: Tensor = nn.functional.interpolate(
        logits, size=size, mode="bilinear", align_corners=False
    )
    return resized


def decode_ltrb_to_boxes(
    box_ltrb: Tensor, grid: tuple[int, int], patch_size: int
) -> Tensor:
    """Turn per-cell ltrb distances into ``(B, Gh*Gw, 4)`` boxes in xywh pixels.

    As with Wave 1's detector, this conversion exists in exactly one place so nothing
    downstream has to guess which convention the numbers are in. The output matches the
    dataset store: xywh, absolute pixels, top-left origin.
    """
    rows, cols = grid
    batch = box_ltrb.shape[0]

    # Cell centres in pixels: the patch at (row, col) covers [col*p, (col+1)*p).
    ys = (torch.arange(rows, device=box_ltrb.device, dtype=box_ltrb.dtype) + 0.5) * patch_size
    xs = (torch.arange(cols, device=box_ltrb.device, dtype=box_ltrb.dtype) + 0.5) * patch_size
    centre_y, centre_x = torch.meshgrid(ys, xs, indexing="ij")

    left, top, right, bottom = box_ltrb.unbind(dim=1)
    x_min = centre_x - left
    y_min = centre_y - top
    width = left + right
    height = top + bottom

    boxes = torch.stack([x_min, y_min, width, height], dim=-1)
    return boxes.reshape(batch, rows * cols, 4)
