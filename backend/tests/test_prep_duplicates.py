"""Scenes by perceptual hash: robust to re-saving, not fooled by different pictures (doc 81)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from app.prep.duplicates import NEAR_DUPLICATE_BITS, clusters, dhash


def _scene(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 255, (24, 32, 3), dtype=np.uint8)
    return Image.fromarray(base).resize((320, 240), Image.Resampling.BICUBIC)


def _bits(a: bytes, b: bytes) -> int:
    return int(
        np.unpackbits(np.bitwise_xor(np.frombuffer(a, np.uint8), np.frombuffer(b, np.uint8))).sum()
    )


def test_a_resized_low_quality_copy_hashes_within_the_threshold(tmp_path: Path) -> None:
    original, copy = tmp_path / "a.png", tmp_path / "b.jpg"
    _scene(1).save(original)
    _scene(1).resize((200, 150)).save(copy, quality=40)
    a, b = dhash(str(original)), dhash(str(copy))
    assert a is not None and b is not None
    assert _bits(a, b) <= NEAR_DUPLICATE_BITS


def test_a_different_picture_is_far_away(tmp_path: Path) -> None:
    _scene(1).save(tmp_path / "a.png")
    _scene(2).save(tmp_path / "b.png")
    a, b = dhash(str(tmp_path / "a.png")), dhash(str(tmp_path / "b.png"))
    assert a is not None and b is not None
    assert _bits(a, b) > 4 * NEAR_DUPLICATE_BITS


def test_an_unreadable_file_hashes_to_none(tmp_path: Path) -> None:
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")
    assert dhash(str(broken)) is None


def test_clusters_group_matches_and_leave_singletons_out() -> None:
    zero, near, far = bytes(32), bytes([1]) + bytes(31), bytes([255]) * 32
    groups = clusters([("a", zero), ("b", near), ("c", far)])
    assert groups == [["a", "b"]]
