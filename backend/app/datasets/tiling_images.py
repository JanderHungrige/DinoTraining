"""Cutting the actual image files to match a retiled document.

Split from `tiling.py` for the 300-line rule, and the seam is real: that module is
arithmetic over a COCO document and opens nothing, this one is I/O and opens every frame.

The two must agree or the result is silently wrong — a retiled document pointing at whole
frames trains on full images with tile-local boxes, every box in the wrong place, and
nothing raises. `plan_tiles` is called from here with the same arguments rather than the
crops being derived from the document, so there is one definition of the grid.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PIL import Image

from app.datasets.tiling import DEFAULT_OVERLAP, plan_tiles, tiled_name

logger = logging.getLogger(__name__)


def write_tiles(
    document: dict[str, Any],
    source_root: Path,
    target_root: Path,
    columns: int,
    rows: int,
    overlap: float = DEFAULT_OVERLAP,
) -> int:
    """Cut the actual images to match a retiled document. Returns how many were written.

    **Only the tiles the document names are written.** `retile` caps how many empty tiles
    it keeps, so cutting the whole grid would leave five files on disk for every one the
    dataset refers to — and the next importer to glob the folder would pick them all up.

    Opens each frame **once** and writes every tile it needs, rather than reopening per
    tile: a 4112 px PNG costs far more to decode than to crop, and a 24-tile grid would
    otherwise decode it twenty-four times.

    Written as PNG only when the source is; otherwise JPEG quality 95. Re-encoding a
    detection dataset at a low quality is a silent way to lose the small objects that are
    the whole reason for tiling.
    """
    wanted = {str(entry["file_name"]) for entry in document["images"]}
    by_frame: dict[str, set[str]] = {}
    for name in wanted:
        # `_r{row}c{column}` was appended by `tiled_name`; recover the frame it came from.
        stem, _, _ = name.rpartition("_r")
        by_frame.setdefault(f"{stem}{Path(name).suffix}", set()).add(name)

    written = 0
    for source_name in sorted(by_frame):
        source = source_root / source_name
        if not source.is_file():
            logger.warning("Frame missing, skipping its tiles: %s", source)
            continue

        with Image.open(source) as frame:
            frame.load()
            for tile in plan_tiles(frame.width, frame.height, columns, rows, overlap):
                name = tiled_name(source_name, tile)
                if name not in by_frame[source_name]:
                    continue
                crop = frame.crop((tile.x, tile.y, tile.x + tile.width, tile.y + tile.height))
                target = target_root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.suffix.lower() == ".png":
                    crop.save(target)
                else:
                    crop.convert("RGB").save(target, quality=95)
                written += 1

    logger.info("Wrote %d tile image(s) under %s", written, target_root)
    return written


__all__ = ["write_tiles"]
