"""Training on tiles, as a recipe planned it (docs 85, 90).

Doc 85's plan says when the objects are too small for the model at the whole picture's
scale, and which grid fixes that. This cuts every training sample into that grid, using
`plan_tiles` and `grid_for`, the same definitions the preview and tiled inference (doc 62)
use. A head trained on tiles must be run on tiles, and the three agreeing is what makes
that true.

Per tile:

* a box at least half inside becomes a target, clipped to the tile;
* a box less than half inside becomes an ignore region: it is really there, so it must
  not be taught as background, and too little of it shows to learn from;
* empty tiles are kept at `DEFAULT_BACKGROUND_RATIO` per tile with a target (doc 49's
  measurement: uncapped, a fixed camera gives ~11 empty tiles per useful one, and the
  detector learns that nothing is almost always right).

Segmentation samples are left whole: doc 85 does not tile outlines.
"""

from __future__ import annotations

import random
from dataclasses import replace

from app.datasets.tiling import (
    DEFAULT_BACKGROUND_RATIO,
    DEFAULT_OVERLAP,
    Tile,
    grid_for,
    plan_tiles,
)
from app.ml.training.samples import TrainingSample

#: A box counts as a target in a tile when at least this share of it is inside.
VISIBLE_SHARE = 0.5

Rect = tuple[float, float, float, float]


def _clip(box: Rect, tile: Tile) -> tuple[Rect | None, float]:
    """The part of `box` inside `tile`, in tile coordinates, and the share that is."""
    x, y, w, h = box
    left, top = max(x, tile.x), max(y, tile.y)
    right, bottom = min(x + w, tile.x + tile.width), min(y + h, tile.y + tile.height)
    if right <= left or bottom <= top:
        return None, 0.0
    share = (right - left) * (bottom - top) / max(1e-9, w * h)
    return (left - tile.x, top - tile.y, right - left, bottom - top), share


def _tile_sample(sample: TrainingSample, tile: Tile) -> TrainingSample:
    targets: list[tuple[int, float, float, float, float]] = []
    ignore: list[Rect] = []
    for cls, *box in sample.targets:
        clipped, share = _clip((box[0], box[1], box[2], box[3]), tile)
        if clipped is None:
            continue
        if share >= VISIBLE_SHARE:
            targets.append((cls, *clipped))
        else:
            ignore.append(clipped)
    for region in sample.ignore_regions:
        clipped, _ = _clip(region, tile)
        if clipped is not None:
            ignore.append(clipped)
    return replace(
        sample,
        width=tile.width,
        height=tile.height,
        targets=tuple(targets),
        ignore_regions=tuple(ignore),
        crop=(tile.x, tile.y, tile.width, tile.height),
    )


def tile_samples(
    samples: list[TrainingSample],
    long_edge_tiles: int,
    overlap: float = DEFAULT_OVERLAP,
    seed: int = 42,
) -> list[TrainingSample]:
    """Every sample cut into its grid; empty tiles capped per image."""
    if long_edge_tiles <= 1:
        return samples
    rng = random.Random(seed)
    tiled: list[TrainingSample] = []
    for sample in samples:
        if sample.masks or sample.ignore_masks:
            tiled.append(sample)
            continue
        columns, rows = grid_for(sample.width, sample.height, long_edge_tiles)
        pieces = [
            _tile_sample(sample, t)
            for t in plan_tiles(sample.width, sample.height, columns, rows, overlap)
        ]
        useful = [p for p in pieces if p.targets]
        empty = [p for p in pieces if not p.targets]
        keep = max(1, int(len(useful) * DEFAULT_BACKGROUND_RATIO)) if useful else 1
        tiled.extend(useful + rng.sample(empty, min(keep, len(empty))))
    return tiled


__all__ = ["VISIBLE_SHARE", "tile_samples"]
