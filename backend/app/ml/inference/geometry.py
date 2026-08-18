"""Putting predictions back into the original image's coordinate system.

The mirror of ``transform_boxes`` / ``transform_mask`` in :mod:`app.ml.preprocess`,
which move *targets* into the training frame. This module moves *predictions* the other
way, and the two are meant to be read together — if you edit one, look at the other.

They live apart because they serve different callers: the forward pair is a training
concern (the trainer is its only consumer), the inverse is an inference one. Should a
third consumer of either direction appear, unify them into a single geometry module.

**Why this exists at all:** a detector running on a letterboxed 448x448 frame returns
boxes in *that* frame. Drawn on the user's 200x900 original without inversion, every box
is offset by the padding and scaled wrong — and it looks *almost* right, which reads as a
bad model rather than a bad transform.

One formula covers both geometries. ``_center_crop`` records a **negative** pad, so
``frame = source * scale + pad`` holds for letterboxing and cropping alike, and the
inverse is the same expression rearranged.
"""

from __future__ import annotations

from typing import Literal

import torch
from torch import Tensor

from app.ml.preprocess import GeometryTransform

#: xywh in absolute pixels, top-left origin — the dataset store's convention.
Box = tuple[float, float, float, float]

ResampleMode = Literal["nearest", "bilinear"]


def invert_point(transform: GeometryTransform, x: float, y: float) -> tuple[float, float]:
    """Frame coordinates back to source coordinates."""
    return (x - transform.pad_x) / transform.scale, (y - transform.pad_y) / transform.scale


def invert_boxes(transform: GeometryTransform, boxes: list[Box]) -> list[Box]:
    """Move xywh boxes from the transformed frame back onto the source image.

    Clipped to the source: a detector can and does predict into the letterbox padding,
    and those pixels do not exist in the user's image. Unlike ``transform_boxes`` this
    does not drop anything — a prediction with no overlap is the model's answer, not a
    corrupt annotation, so it is clamped rather than discarded and no index bookkeeping
    is needed.
    """
    source_w, source_h = transform.source_size
    recovered: list[Box] = []

    for x, y, w, h in boxes:
        left, top = invert_point(transform, x, y)
        # Extent divides by scale too. Inverting only the origin is the classic
        # half-right inversion: boxes land in the right place with the wrong size.
        width, height = w / transform.scale, h / transform.scale

        right = min(left + width, float(source_w))
        bottom = min(top + height, float(source_h))
        # The origin is clamped to the source on *both* sides. Clamping only at zero
        # leaves a box predicted entirely inside the padding sitting at y=361 on a
        # 300px image: its height collapses to zero but its origin stays outside the
        # picture, so "in source coordinates" quietly stops being true.
        left = min(max(left, 0.0), float(source_w))
        top = min(max(top, 0.0), float(source_h))

        recovered.append((left, top, max(right - left, 0.0), max(bottom - top, 0.0)))

    return recovered


def invert_map(
    transform: GeometryTransform, frame: Tensor, mode: ResampleMode = "nearest"
) -> Tensor:
    """Move a dense ``(H, W)`` prediction from the frame back onto the source image.

    Two steps, in this order:

    1. **Crop the padding away.** The grey bars a letterbox added are not part of the
       image; leaving them in and rescaling would squash the content and drag padding
       values into the output.
    2. **Resample to the source resolution.**

    ``mode`` is not a detail. Use ``nearest`` for label maps — bilinear resampling of
    class ids averages them and invents classes nobody annotated, which is the same trap
    ``transform_mask`` documents for the forward direction. Use ``bilinear`` for depth,
    where the values are continuous and interpolation is meaningful.
    """
    source_w, source_h = transform.source_size

    content_w = max(1, round(source_w * transform.scale))
    content_h = max(1, round(source_h * transform.scale))
    left, top = int(round(transform.pad_x)), int(round(transform.pad_y))

    # Clamped to what the frame actually holds. A centre crop records a negative pad
    # because it discarded content, so the requested window can start outside the frame.
    y0, x0 = max(top, 0), max(left, 0)
    y1 = min(top + content_h, frame.shape[-2])
    x1 = min(left + content_w, frame.shape[-1])
    cropped = frame[..., y0:y1, x0:x1]

    resized = torch.nn.functional.interpolate(
        cropped[None, None].float(),
        size=(source_h, source_w),
        mode=mode,
        **({} if mode == "nearest" else {"align_corners": False}),
    )
    return resized[0, 0]
