"""The ways a published dataset writes a box, and turning each into the store's (doc 82).

The store holds ``x, y, w, h`` in absolute pixels from the top-left, which is COCO's own
convention. Many exports claim to be COCO and are not. Common alternatives are corner pairs
(``x1, y1, x2, y2``) and values normalised to 0–1. Read as the wrong convention, every box
is either skipped as "outside the frame" or, worse, silently shifted, and the import reports
success either way. Doc 82's intake decides which convention a file actually uses, from
evidence, before anything is written.
"""

from __future__ import annotations

from typing import Literal

Convention = Literal["xywh", "xyxy", "xywh-normalized"]
CONVENTIONS: tuple[Convention, ...] = ("xywh", "xyxy", "xywh-normalized")


def to_xywh(
    bbox: tuple[float, float, float, float], convention: Convention, width: int, height: int
) -> tuple[float, float, float, float]:
    """One box in the store's convention: absolute ``x, y, w, h``."""
    a, b, c, d = bbox
    if convention == "xyxy":
        return a, b, c - a, d - b
    if convention == "xywh-normalized":
        return a * width, b * height, c * width, d * height
    return a, b, c, d


__all__ = ["CONVENTIONS", "Convention", "to_xywh"]
