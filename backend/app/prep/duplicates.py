"""Near-duplicate images, by perceptual difference hash (doc 81).

Near-duplicates matter twice: they inflate a dataset without adding information, and when
copies land on both sides of a train/validation split the validation score measures memory
rather than learning. That is doc 49's 42% inflated mAP.

**dHash, not a byte hash.** Two exports of one photo at different JPEG qualities, or one
resized, share almost no bytes and nearly all of their dHash: 256 bits recording whether
each pixel of a 17×16 greyscale thumbnail is brighter than its right-hand neighbour.

**Same picture is not the same example.** Measured on the chess dataset (2026-09-29): pairs
at distance 0 whose pixels differ by 1.5/255 on average, because one photo has a white
knight in the corner and the other a black king. The scene is identical and the annotation
is not, so "keep one" would have deleted correct, different examples. This module therefore
only groups *scenes*. `audit.py` calls a group a copy only when the annotations match too.
Scene groups are still what the split keeps together (doc 84): the background is shared.

What this does *not* catch is two different photographs of the same scene. Consecutive video
frames are the common case, and those are grouped by their sequence instead (doc 84).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

#: Hash side: 16×16 gradient signs = 256 bits. 8×8 chained all but five of 289 chess
#: photos into one group; 16×16 resolves them.
HASH_SIDE = 16

#: Bits (of 256, ~3 %) two images may differ by and still be "the same scene".
NEAR_DUPLICATE_BITS = 8

_POPCOUNT = np.array([bin(value).count("1") for value in range(256)], dtype=np.uint8)


def dhash(path: str) -> bytes | None:
    """The 256-bit difference hash of an image, or None when it cannot be read."""
    try:
        with Image.open(path) as image:
            image.draft("L", (128, 128))  # JPEG: decode at reduced size, much faster
            small = image.convert("L").resize((HASH_SIDE + 1, HASH_SIDE), Image.Resampling.LANCZOS)
            pixels = np.asarray(small, dtype=np.int16)
    except (OSError, ValueError) as error:
        logger.info("Cannot hash %s: %s", path, error)
        return None
    bits = (pixels[:, 1:] > pixels[:, :-1]).flatten()
    return bytes(np.packbits(bits))


def clusters(
    hashes: Iterable[tuple[str, bytes]], max_bits: int = NEAR_DUPLICATE_BITS
) -> list[list[str]]:
    """Groups of paths whose hashes are within `max_bits` of each other (transitively).

    Pairwise, one vectorised row at a time: 5,000 images is 12.5M comparisons, about a
    second in numpy.
    """
    items = list(hashes)
    if len(items) < 2:
        return []
    values = np.stack([np.frombuffer(value, dtype=np.uint8) for _, value in items])
    parent = list(range(len(items)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(items) - 1):
        diff = np.bitwise_xor(values[i + 1 :], values[i])
        distance = _POPCOUNT[diff].sum(axis=1)
        for offset in np.nonzero(distance <= max_bits)[0]:
            parent[root(i + 1 + int(offset))] = root(i)

    groups: dict[int, list[str]] = {}
    for i, (path, _) in enumerate(items):
        groups.setdefault(root(i), []).append(path)
    return [group for group in groups.values() if len(group) > 1]


__all__ = ["NEAR_DUPLICATE_BITS", "clusters", "dhash"]
