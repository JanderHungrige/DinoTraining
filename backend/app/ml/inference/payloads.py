"""Shaping a decoder's output for the renderer, in source coordinates.

Split out of ``engine.py`` when the dense payloads changed transport — doc 18 recorded
that the next change to payload shaping should land here rather than push the engine past
the 300-line gate.

Dispatch is keyed off ``render_hint``, never off the task string: two head types can share
a task and a renderer, and the hint is what feature 20 draws from.

**Dense maps travel as PNG, not as nested JSON lists.** A 3000x2000 segmentation is
18.5 MB of JSON numbers and 17 KB as a base64 PNG — measured, 1080x. The numbers are
mostly redundant: the map is upsampled from a 32x32 patch grid, so millions of JSON
integers encode a few thousand values of real signal, and PNG's run-length filtering
removes exactly that redundancy. The client draws the PNG to a canvas, which is also less
work than building ImageData from nested arrays.
"""

from __future__ import annotations

import base64
import io

import numpy as np
import torch
from PIL import Image

from app.ml.heads.modules import upsample_logits
from app.ml.heads.registry import HeadTypeSpec
from app.ml.inference.geometry import invert_boxes, invert_map
from app.ml.preprocess import GeometryTransform

#: Detections kept for display. The decoder already ranks by score.
MAX_DISPLAY_BOXES = 50

#: Class indices are transported in one byte, so a head with more classes than this
#: cannot use the PNG path. Today's widest is ADE20k at 150.
MAX_PNG_CLASSES = 256


def to_numpy(tensor: torch.Tensor) -> np.ndarray:
    """Bring a tensor to host memory before numpy touches it.

    ``.numpy()`` raises on any tensor that is not a plain CPU leaf — an MPS or CUDA
    tensor, or one still attached to the graph. The previous transport used ``.tolist()``,
    which quietly accepts all three, so this only became reachable when the dense maps
    moved to PNG. Every conversion in this module goes through here so there is one place
    for it to be right.
    """
    return tensor.detach().cpu().numpy()


def encode_png(array: np.ndarray) -> str:
    """One-channel uint8 array → base64 PNG, for embedding in a JSON payload."""
    buffer = io.BytesIO()
    Image.fromarray(array, mode="L").save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def build_payload(
    spec: HeadTypeSpec,
    decoded: dict[str, torch.Tensor],
    transform: GeometryTransform,
    frame_size: int,
    score_threshold: float,
) -> dict[str, object]:
    """Shape the decoder's output for the render hint, in source coordinates."""
    if spec.render_hint == "labels":
        return labels_payload(decoded)
    if spec.render_hint == "boxes":
        return boxes_payload(decoded, transform, score_threshold)
    if spec.render_hint == "masks":
        return masks_payload(decoded, transform, frame_size)
    return depth_payload(decoded, transform, frame_size)


def labels_payload(decoded: dict[str, torch.Tensor]) -> dict[str, object]:
    logits = decoded["logits"][0]
    scores = torch.softmax(logits.float(), dim=-1)
    return {"scores": [float(value) for value in scores]}


def boxes_payload(
    decoded: dict[str, torch.Tensor], transform: GeometryTransform, threshold: float
) -> dict[str, object]:
    scores = decoded["scores"]
    keep = scores >= threshold
    if not bool(keep.any()):
        return {"boxes": [], "scores": [], "classes": []}

    kept_boxes = decoded["boxes"][keep][:MAX_DISPLAY_BOXES]
    kept_scores = scores[keep][:MAX_DISPLAY_BOXES]
    kept_classes = decoded["classes"][keep][:MAX_DISPLAY_BOXES]

    frame_boxes = [tuple(float(v) for v in box) for box in kept_boxes]
    source_boxes = invert_boxes(transform, frame_boxes)  # type: ignore[arg-type]

    # A box predicted entirely inside the letterbox padding inverts to zero area: it
    # describes pixels the user's image does not have. Dropped here rather than left
    # for the renderer to filter — and dropped from all three arrays together, because
    # they are read positionally and a partial drop misaligns every later score.
    survivors = [
        (box, float(score), int(cls))
        for box, score, cls in zip(source_boxes, kept_scores, kept_classes, strict=True)
        if box[2] > 0.0 and box[3] > 0.0
    ]

    return {
        "boxes": [list(box) for box, _, _ in survivors],
        "scores": [score for _, score, _ in survivors],
        "classes": [cls for _, _, cls in survivors],
    }


def masks_payload(
    decoded: dict[str, torch.Tensor], transform: GeometryTransform, frame_size: int
) -> dict[str, object]:
    # Patch resolution -> frame resolution -> source resolution. The head has no idea
    # what size to upsample to, which is why upsample_logits takes it explicitly.
    logits = decoded["logits"]
    at_frame = upsample_logits(logits.float(), (frame_size, frame_size))
    classes = at_frame[0].argmax(dim=0).float()
    # nearest: bilinear on a label map averages class ids into classes nobody predicted.
    at_source = invert_map(transform, classes, mode="nearest").round().to(torch.int64)

    indices = to_numpy(at_source).astype(np.int64)
    present = sorted({int(value) for value in np.unique(indices)})
    if present and present[-1] >= MAX_PNG_CLASSES:
        # Not reachable with any head shipped today; a loud failure beats silently
        # wrapping class 300 round to class 44 in a byte.
        raise ValueError(
            f"Class index {present[-1]} exceeds the {MAX_PNG_CLASSES}-class PNG transport."
        )

    return {
        "mask_png": encode_png(indices.astype(np.uint8)),
        # The pixel value *is* the class index — no palette, so the client owns colour.
        "present_classes": present,
        "height": int(at_source.shape[0]),
        "width": int(at_source.shape[1]),
    }


def depth_payload(
    decoded: dict[str, torch.Tensor], transform: GeometryTransform, frame_size: int
) -> dict[str, object]:
    depth = decoded["depth"].float()
    at_frame = torch.nn.functional.interpolate(
        depth, size=(frame_size, frame_size), mode="bilinear", align_corners=False
    )
    # bilinear here: depth is continuous, so interpolation is meaningful — the opposite
    # of the label-map case above.
    at_source = invert_map(transform, at_frame[0, 0], mode="bilinear")

    low = float(at_source.min())
    high = float(at_source.max())
    # Normalised to 0..255 for transport. This is a *display* encoding: 256 levels across
    # a scene's depth range is finer than the eye reads off a colour ramp, and `min`/`max`
    # are carried so a consumer can map a pixel back to metres. Anything needing true
    # metric depth should take it from the tensor rather than from this payload.
    span = high - low
    normalised = (at_source - low) / span if span > 0 else torch.zeros_like(at_source)
    scaled = to_numpy((normalised * 255.0).round().clamp(0, 255)).astype(np.uint8)

    return {
        "depth_png": encode_png(scaled),
        "min": low,
        "max": high,
        "height": int(at_source.shape[0]),
        "width": int(at_source.shape[1]),
    }
