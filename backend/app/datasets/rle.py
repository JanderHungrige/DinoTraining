"""COCO run-length encoding for segmentation masks.

The uncompressed COCO form: ``counts`` is a list of alternating run lengths read in
**column-major** order, always starting with a background run — so a fully-foreground mask
leads with a literal ``0``. Both of those are conventions, not implementation details: a
row-major encoding round-trips against its own decoder and is wrong to every other COCO
reader, and a missing leading zero shifts every subsequent run's polarity.

The list form is used rather than ``pycocotools``' compressed byte string because it needs no
C-extension dependency in an app that installs on three platforms, and run-length encoding
already provides the large win over a dense mask.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

#: (height, width) — COCO's ``size`` field order, which is *not* (width, height).
Size = tuple[int, int]
Bbox = tuple[float, float, float, float]


def rle_encode(mask: npt.NDArray[np.bool_]) -> tuple[list[int], Size]:
    """Encode a 2-D boolean mask. Returns ``(counts, (height, width))``."""
    if mask.ndim != 2:
        raise ValueError(f"Expected a 2-D mask, got {mask.ndim} dimensions")

    height, width = int(mask.shape[0]), int(mask.shape[1])
    flat = np.asarray(mask, dtype=bool).ravel(order="F")
    if flat.size == 0:
        return [], (height, width)

    # Boundaries are the indices where the value flips; the runs are the gaps between them.
    transitions = np.flatnonzero(flat[1:] != flat[:-1]) + 1
    bounds = np.concatenate(([0], transitions, [flat.size]))
    runs = [int(run) for run in np.diff(bounds)]

    if bool(flat[0]):
        # Counting always begins from background, so a mask that starts foreground needs
        # an explicit empty background run in front of it.
        runs.insert(0, 0)
    return runs, (height, width)


def rle_decode(counts: list[int], size: Size) -> npt.NDArray[np.bool_]:
    """Decode back to a 2-D boolean mask."""
    height, width = size
    validate_counts(counts, height, width)

    flat = np.zeros(height * width, dtype=bool)
    position = 0
    is_foreground = False
    for run in counts:
        if is_foreground and run:
            flat[position : position + run] = True
        position += run
        is_foreground = not is_foreground
    return flat.reshape((height, width), order="F")


def rle_bbox(counts: list[int], size: Size) -> Bbox | None:
    """Tight bounding box as xywh, top-left origin. ``None`` for an empty mask.

    Stored alongside the mask on write so that listing and overlay placement never have to
    decode an RLE — the difference between an indexed query and decoding every mask in a
    dataset to render a list.
    """
    mask = rle_decode(counts, size)
    rows = np.flatnonzero(mask.any(axis=1))
    columns = np.flatnonzero(mask.any(axis=0))
    if rows.size == 0 or columns.size == 0:
        return None

    top, bottom = int(rows[0]), int(rows[-1])
    left, right = int(columns[0]), int(columns[-1])
    return (float(left), float(top), float(right - left + 1), float(bottom - top + 1))


def rle_area(counts: list[int]) -> int:
    """Foreground pixel count — the odd-indexed runs, since counting starts at background."""
    return int(sum(counts[1::2]))


def validate_counts(counts: list[int], height: int, width: int) -> None:
    """Reject a corrupt or hostile encoding *before* anything is allocated.

    This is arithmetic over the list, never a materialised mask, so a caller sending a run
    of ten million against a 2x2 frame costs a sum rather than a gigabyte.
    """
    for run in counts:
        if run < 0:
            raise ValueError(f"Run lengths cannot be negative, got {run}")

    total = sum(counts)
    expected = height * width
    if total != expected:
        raise ValueError(
            f"Run lengths sum to {total}, but a {width}x{height} mask needs exactly {expected}"
        )
