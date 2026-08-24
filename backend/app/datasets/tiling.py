"""Cutting large frames into tiles, so far-field objects survive the model's input size.

Measured on OSDaR23's `rgb_center`: the median annotated object is **10.7 px across in a
2464 px frame**. A head trains at 448 px input, so that object arrives as **1.9 px** — below
the 7 px stride doc 43's detector predicts on. There is no loss function and no number of
epochs that recovers an object smaller than one cell; it is simply not in the tensor.

Tiling is the standard answer and it is arithmetic, not cleverness: a 4x3 grid over that
frame gives 616 px tiles, in which the same object is 10.7 px of 616 — and at 448 px input,
**7.8 px**. That is above the stride, so the head can represent it.

Kept separate from `openlabel_to_coco.py` because it is not an OpenLABEL concept. Any COCO
document with known frame dimensions can be retiled, and a future importer for far-field
aerial or satellite data would want exactly this.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Fraction of a tile's size that neighbouring tiles share. An object sitting exactly on a
#: seam would otherwise be cut in half in both tiles and be a bad example in each.
DEFAULT_OVERLAP = 0.15

#: How many empty tiles to keep per tile that has a box. Background is real supervision —
#: sky, ballast and vegetation are what this detector must learn to reject — but a fixed
#: camera puts every object in the same part of every frame, so an uncapped grid yields
#: ~11 empty tiles per useful one and the detector learns that predicting nothing is
#: almost always right. Measured on OSDaR23: 1078 of 1176 tiles held no box at all.
DEFAULT_BACKGROUND_RATIO = 1.0


@dataclass(frozen=True, slots=True)
class Tile:
    x: int
    y: int
    width: int
    height: int
    column: int
    row: int

    def suffix(self) -> str:
        return f"_r{self.row}c{self.column}"


@dataclass(frozen=True, slots=True)
class TilingSummary:
    tiles_per_frame: int = 0
    images: int = 0
    boxes: int = 0
    #: Tiles containing no box at all. Kept, not dropped — see the rule below.
    empty_tiles: int = 0
    dropped_boxes: int = 0


def plan_tiles(
    width: int, height: int, columns: int, rows: int, overlap: float = DEFAULT_OVERLAP
) -> list[Tile]:
    """The grid, with overlap, clamped so the last tile ends exactly at the frame edge."""
    if columns < 1 or rows < 1:
        raise ValueError(f"Need at least a 1x1 grid, got {columns}x{rows}")
    if not 0.0 <= overlap < 1.0:
        raise ValueError(f"overlap must be in [0, 1), got {overlap}")

    tile_width = int(round(width / columns * (1.0 + overlap)))
    tile_height = int(round(height / rows * (1.0 + overlap)))
    # Step is the *non-overlapping* advance, so `columns` steps still span the frame.
    step_x = (width - tile_width) / (columns - 1) if columns > 1 else 0.0
    step_y = (height - tile_height) / (rows - 1) if rows > 1 else 0.0

    return [
        Tile(
            x=int(round(column * step_x)),
            y=int(round(row * step_y)),
            width=min(tile_width, width),
            height=min(tile_height, height),
            column=column,
            row=row,
        )
        for row in range(rows)
        for column in range(columns)
    ]


def retile(
    document: dict[str, Any],
    width: int,
    height: int,
    columns: int,
    rows: int,
    overlap: float = DEFAULT_OVERLAP,
    background_ratio: float = DEFAULT_BACKGROUND_RATIO,
) -> tuple[dict[str, Any], TilingSummary]:
    """One COCO document over full frames, as one over tiles.

    **A box belongs to exactly one tile: the one whose centre is nearest to the box's**,
    among those containing it, and it is clipped to that tile.

    "The tile its centre falls in" is not enough, and a test caught that: tiles overlap by
    design, so a box in the shared strip has its centre inside *two* of them and would be
    emitted twice. Duplication is the failure mode to fear here because it looks like
    success — more training data, and every count downstream inflates, metrics included.
    Nearest-centre also picks the tile where the object sits furthest from an edge, which
    is the better example of the two.

    **Empty tiles are kept, but capped.** Sky and ballast are the background this detector
    must learn to reject, so dropping them entirely teaches it that every image contains
    something. Keeping all of them is the opposite mistake: a fixed camera puts every object
    in the same part of every frame, so the grid is overwhelmingly background — 1078 of 1176
    tiles on OSDaR23 — and predicting nothing scores well. `background_ratio` caps empties
    at that multiple of the tiles that do hold a box, sampled evenly across the sequence so
    the background is varied rather than all taken from the first frames.
    """
    tiles = plan_tiles(width, height, columns, rows, overlap)
    by_image: dict[int, list[dict[str, Any]]] = {}
    for annotation in document["annotations"]:
        by_image.setdefault(int(annotation["image_id"]), []).append(annotation)

    # Two passes: which tiles hold a box, then which of the rest to keep. Deciding as we
    # go is not possible — the cap depends on a total that is only known at the end.
    populated: list[tuple[int, int]] = []
    barren: list[tuple[int, int]] = []
    ownership: dict[tuple[int, int], list[int]] = {}
    for source_index, source in enumerate(document["images"]):
        source_boxes = by_image.get(int(source["id"]), [])
        owners = [_owning_tile(a["bbox"], tiles) for a in source_boxes]
        for tile_index in range(len(tiles)):
            held = [i for i, owner in enumerate(owners) if owner == tile_index]
            ownership[(source_index, tile_index)] = held
            (populated if held else barren).append((source_index, tile_index))

    if populated:
        allowance = round(len(populated) * background_ratio)
        keep = set(populated) | set(_sample_evenly(barren, allowance))
    else:
        # Nothing to balance against. A document with no boxes is a legitimate input — an
        # unlabelled folder being prepared for annotation — and returning no tiles at all
        # for it would be a silent, total loss.
        keep = set(barren)

    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    empty = 0

    for source_index, source in enumerate(document["images"]):
        source_boxes = by_image.get(int(source["id"]), [])
        for tile_index, tile in enumerate(tiles):
            if (source_index, tile_index) not in keep:
                continue
            held = ownership[(source_index, tile_index)]
            image_id = len(images) + 1
            images.append(
                {
                    "id": image_id,
                    "file_name": tiled_name(str(source["file_name"]), tile),
                    "width": tile.width,
                    "height": tile.height,
                }
            )
            for index in held:
                annotation = source_boxes[index]
                clipped = _clip(annotation["bbox"], tile)
                if clipped is None:  # pragma: no cover - ownership implies overlap
                    continue
                annotations.append(
                    {
                        "id": len(annotations) + 1,
                        "image_id": image_id,
                        "category_id": annotation["category_id"],
                        "bbox": [round(v, 2) for v in clipped],
                        "area": round(clipped[2] * clipped[3], 2),
                        "iscrowd": 0,
                    }
                )
            if not held:
                empty += 1

    dropped = len(document["annotations"]) - len(annotations)
    tiled = dict(document)
    tiled["images"] = images
    tiled["annotations"] = annotations
    logger.info(
        "Retiled %d frame(s) into %d tile(s); %d box(es) placed, %d unplaced",
        len(document["images"]),
        len(images),
        len(annotations),
        dropped,
    )
    return tiled, TilingSummary(
        tiles_per_frame=len(tiles),
        images=len(images),
        boxes=len(annotations),
        empty_tiles=empty,
        dropped_boxes=max(0, dropped),
    )


def _sample_evenly(items: list[tuple[int, int]], count: int) -> list[tuple[int, int]]:
    """`count` items spread across `items`, deterministically.

    Evenly rather than randomly, and rather than taking a prefix: a prefix would draw every
    background tile from the first few frames, which on a moving train means one stretch of
    line standing in for the whole sequence.
    """
    if count <= 0 or not items:
        return []
    if count >= len(items):
        return list(items)
    stride = len(items) / count
    return [items[int(index * stride)] for index in range(count)]


def _owning_tile(bbox: list[float], tiles: list[Tile]) -> int | None:
    """Index of the single tile this box belongs to, or None when no tile holds its centre.

    Among the tiles containing the centre — there can be several, because tiles overlap —
    the nearest by centre distance wins. Ties break on tile order, so the result does not
    depend on dictionary iteration.
    """
    x, y, w, h = (float(v) for v in bbox)
    centre_x, centre_y = x + w / 2.0, y + h / 2.0

    best: int | None = None
    best_distance = float("inf")
    for index, tile in enumerate(tiles):
        if not (tile.x <= centre_x < tile.x + tile.width):
            continue
        if not (tile.y <= centre_y < tile.y + tile.height):
            continue
        tile_centre_x = tile.x + tile.width / 2.0
        tile_centre_y = tile.y + tile.height / 2.0
        distance = (centre_x - tile_centre_x) ** 2 + (centre_y - tile_centre_y) ** 2
        if distance < best_distance:
            best, best_distance = index, distance
    return best


def tiled_name(file_name: str, tile: Tile) -> str:
    path = Path(file_name)
    return str(path.with_name(f"{path.stem}{tile.suffix()}{path.suffix}"))


def _clip(bbox: list[float], tile: Tile) -> tuple[float, float, float, float] | None:
    """The box in tile-local coordinates, clipped to the tile."""
    x, y, w, h = (float(v) for v in bbox)
    left = max(x, float(tile.x)) - tile.x
    top = max(y, float(tile.y)) - tile.y
    right = min(x + w, float(tile.x + tile.width)) - tile.x
    bottom = min(y + h, float(tile.y + tile.height)) - tile.y
    if right <= left or bottom <= top:  # pragma: no cover - centre inside implies overlap
        return None
    return (left, top, right - left, bottom - top)


__all__ = [
    "DEFAULT_BACKGROUND_RATIO",
    "DEFAULT_OVERLAP",
    "Tile",
    "TilingSummary",
    "plan_tiles",
    "retile",
    "tiled_name",
]
