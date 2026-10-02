"""COCO `segmentation` as the app's masks (doc 136).

Doc 31's importer kept boxes only; polygons and RLE masks were dropped without a word.
Three shapes arrive:
- **polygons** (`[[x1, y1, x2, y2, …], …]`), drawn with Pillow;
- **uncompressed RLE** (`{"counts": [..], "size": [h, w]}`): already the app's own form
  (column-major, background first, rle.py);
- **compressed RLE** (`counts` as pycocotools' string), decoded here without the C
  extension, by its published algorithm.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from app.datasets.models import Mask, MaskRle
from app.datasets.rle import rle_encode


def decompress_counts(text: str) -> list[int]:
    """pycocotools' `rleFrString`: 5-bit groups, sign bit, delta from two runs back."""
    counts: list[int] = []
    position = 0
    while position < len(text):
        value, shift, more = 0, 0, True
        while more:
            chunk = ord(text[position]) - 48
            value |= (chunk & 0x1F) << (5 * shift)
            more = bool(chunk & 0x20)
            position += 1
            shift += 1
            if not more and chunk & 0x10:
                value |= -1 << (5 * shift)
        if len(counts) > 2:
            value += counts[-2]
        counts.append(value)
    return counts


def _polygon_mask(polygons: list[list[float]], width: int, height: int) -> np.ndarray:
    canvas = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(canvas)
    for polygon in polygons:
        points = list(zip(polygon[0::2], polygon[1::2], strict=False))
        if len(points) >= 3:
            draw.polygon(points, fill=1)
    return np.asarray(canvas, dtype=bool)


def mask_rle(segmentation: object, width: int, height: int) -> MaskRle | None:
    """One annotation's segmentation as the app's RLE, or None if it has none usable."""
    if isinstance(segmentation, list) and segmentation:
        polygons = [p for p in segmentation if isinstance(p, list) and len(p) >= 6]
        if not polygons:
            return None
        mask = _polygon_mask(polygons, width, height)
        if not mask.any():
            return None
        counts, size = rle_encode(mask)
        return MaskRle(size=size, counts=counts)
    if isinstance(segmentation, dict):
        declared = segmentation.get("size")
        raw = segmentation.get("counts")
        if not isinstance(declared, list) or len(declared) != 2:
            return None
        if (int(declared[0]), int(declared[1])) != (height, width):
            return None
        runs = decompress_counts(raw) if isinstance(raw, str) else raw
        if isinstance(runs, list) and sum(int(c) for c in runs) == height * width:
            return MaskRle(size=(height, width), counts=[int(c) for c in runs])
    return None


def masks_for_image(
    entries: list[dict[str, Any]], categories: dict[int, str], width: int, height: int
) -> list[Mask]:
    masks = []
    for entry in entries:
        name = categories.get(int(entry.get("category_id", -1)))
        rle = mask_rle(entry.get("segmentation"), width, height) if name else None
        if rle is not None:
            masks.append(Mask(label="positive", provenance="imported", rle=rle, prompt=name))
    return masks
