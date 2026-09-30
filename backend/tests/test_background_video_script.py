"""The background loop's frame order (doc 76).

The seam is only invisible if no frame is shown twice in a row: not at the far end, where
the clip turns round, and not at the loop point, where it restarts.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_background_video.py"
spec = importlib.util.spec_from_file_location("build_background_video", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_forwards_then_backwards_without_repeating_either_end() -> None:
    assert module.mirror_order(5) == [0, 1, 2, 3, 4, 3, 2, 1]


def test_no_frame_follows_itself_even_across_the_loop_point() -> None:
    order = module.mirror_order(870)
    looped = [*order, order[0]]
    assert all(a != b for a, b in zip(looped, looped[1:], strict=False))
    # Every step is to a neighbouring frame, so the motion never jumps.
    assert all(abs(a - b) == 1 for a, b in zip(looped, looped[1:], strict=False))


def test_tiny_clips_do_not_break() -> None:
    assert module.mirror_order(1) == [0]
    assert module.mirror_order(0) == []
