"""Brush and eraser on a stored outline (doc 106): discs stamped along a stroke.

On the server rather than in a browser canvas: WebKit dithers pixel data that passes
through a canvas (memory `dinotraining-webkit-canvas-data`), so a mask painted there could
differ from what was drawn. Here it is exact, and returns the RLE the store keeps.
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

Point = tuple[float, float]


def _stamp(mask: npt.NDArray[np.bool_], cx: float, cy: float, radius: float, value: bool) -> None:
    height, width = mask.shape
    x0, x1 = max(0, math.floor(cx - radius)), min(width, math.ceil(cx + radius) + 1)
    y0, y1 = max(0, math.floor(cy - radius)), min(height, math.ceil(cy + radius) + 1)
    if x0 >= x1 or y0 >= y1:
        return
    ys, xs = np.ogrid[y0:y1, x0:x1]
    disc = (xs + 0.5 - cx) ** 2 + (ys + 0.5 - cy) ** 2 <= radius**2
    mask[y0:y1, x0:x1][disc] = value


def apply_stroke(
    mask: npt.NDArray[np.bool_], points: list[Point], radius: float, erase: bool
) -> npt.NDArray[np.bool_]:
    """A copy of `mask` with a stroke of discs of `radius` along `points` painted (or
    erased). Consecutive points are joined, sampled at a quarter of the radius, so a fast
    drag leaves no gaps."""
    if radius <= 0:
        raise ValueError("The brush size must be above zero.")
    out = mask.copy()
    step = max(0.5, radius / 4)
    previous: Point | None = None
    for point in points:
        if previous is None:
            _stamp(out, point[0], point[1], radius, not erase)
        else:
            distance = math.dist(previous, point)
            count = max(1, math.ceil(distance / step))
            for i in range(1, count + 1):
                t = i / count
                x = previous[0] + (point[0] - previous[0]) * t
                y = previous[1] + (point[1] - previous[1]) * t
                _stamp(out, x, y, radius, not erase)
        previous = point
    return out


__all__ = ["apply_stroke"]
