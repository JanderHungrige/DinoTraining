"""Worst-case text contrast over the background loop (doc 80).

    backend/.venv/bin/python scripts/check_background_contrast.py

Finds the brightest and the darkest pixel anywhere in the loop (every 10th frame, at blur scale),
composites it exactly as the browser stacks the layers — video, scrim, translucent
surface — and reports each text colour's WCAG contrast against the result. Exits 1 if any
falls below AA (4.5:1).

**The constants below must match look.css / styles.css.** They are repeated here rather
than parsed, because a CSS parser for three custom properties would be the larger risk;
change them together, and rerun this whenever the loop, a surface or a token changes.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

LOOP = (
    Path(__file__).resolve().parents[1]
    / "apps/frontend/public/background/particles-loop.mp4"
)
AA = 4.5


@dataclass(frozen=True)
class Mode:
    bg: str
    raised: str
    scrim: tuple[int, int, int]
    scrim_top: float
    scrim_bottom: float
    panel: float
    header: float
    tokens: dict[str, str]


MODES = {
    "dark": Mode(
        bg="#14161a",
        raised="#1c1f26",
        scrim=(10, 11, 14),
        scrim_top=0.25,
        scrim_bottom=0.2,
        panel=0.6,
        header=0.78,
        tokens={
            "text": "#e7e9ee",
            "text-dim": "#b3bac6",
            "accent": "#4ade80",
            "danger": "#fca5a5",
            "pending": "#fbbf24",
        },
    ),
}


def rgb(value: str) -> np.ndarray:
    return np.array([int(value[i : i + 2], 16) for i in (1, 3, 5)]) / 255


def luminance(colour: np.ndarray) -> float:
    linear = np.where(
        colour <= 0.04045, colour / 12.92, ((colour + 0.055) / 1.055) ** 2.4
    )
    return float(0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2])


def contrast(a: np.ndarray, b: np.ndarray) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def extreme_pixels() -> tuple[np.ndarray, np.ndarray]:
    """The brightest and the darkest pixel: dark text fails over the one, light over the other."""
    import av

    best, pixel = -1.0, np.zeros(3)
    least, dark = 2.0, np.zeros(3)
    with av.open(str(LOOP)) as container:
        for index, frame in enumerate(container.decode(container.streams.video[0])):
            if index % 10:
                continue
            small = (
                np.asarray(frame.to_image().resize((128, 72)), dtype=np.float64) / 255
            )
            lum = (
                0.2126 * small[..., 0] + 0.7152 * small[..., 1] + 0.0722 * small[..., 2]
            )
            at = np.unravel_index(lum.argmax(), lum.shape)
            if lum[at] > best:
                best, pixel = float(lum[at]), small[at]
            low = np.unravel_index(lum.argmin(), lum.shape)
            if lum[low] < least:
                least, dark = float(lum[low]), small[low]
    return pixel, dark


def check(mode: str, m: Mode, pixel: np.ndarray) -> bool:
    """Print each token's contrast over `pixel`; True if one falls below AA."""
    scrim = np.array(m.scrim) / 255
    panel = m.panel * rgb(m.bg) + (1 - m.panel) * (
        m.scrim_bottom * scrim + (1 - m.scrim_bottom) * pixel
    )
    header = m.header * rgb(m.raised) + (1 - m.header) * (
        m.scrim_top * scrim + (1 - m.scrim_top) * pixel
    )
    failed = False
    for name, value in m.tokens.items():
        on_panel, on_header = (
            contrast(rgb(value), panel),
            contrast(rgb(value), header),
        )
        flag = "" if min(on_panel, on_header) >= AA else "  <-- below AA"
        failed |= bool(flag)
        print(f"{mode:5s} {name:9s} panel {on_panel:5.2f}  header {on_header:5.2f}{flag}")
    return failed


def main() -> int:
    bright, dark = extreme_pixels()
    failed = False
    for label, pixel in (("brightest", bright), ("darkest", dark)):
        print(f"{label} pixel in the loop: {np.round(pixel * 255).astype(int).tolist()}")
        for mode, m in MODES.items():
            failed |= check(mode, m, pixel)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
