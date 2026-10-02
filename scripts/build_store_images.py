"""The Microsoft Store's images from the V-Rex logo (doc 164).

    backend/.venv/bin/python scripts/build_store_images.py

The logo (`branding/v-rex-logo.png`, 500 px) is two colours on transparency: yellow and
black. Plain upscaling to 2160 px would make every edge soft. So it is upscaled once,
then every pixel is put back on the line between black and yellow, with only a narrow
band of edge smoothing: crisp at any size. The smaller sizes are scaled down from that
master.

Writes into `packaging/store/images/`:
- poster art 9:16, 1440×2160 (logo, name and expansion on the app's dark ground);
- box art 1:1, 2160×2160 (logo on the dark ground);
- app tile icons 1:1, 300, 150 and 71 px (logo on transparency).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "branding" / "v-rex-logo.png"
OUT = ROOT / "packaging" / "store" / "images"

YELLOW = np.array([250.0, 220.0, 2.0])  # measured from the logo
GROUND = (20, 22, 26)  # the app's --bg, #14161a
TEXT_DIM = (179, 186, 198)  # the app's --text-dim, #b3bac6
FONT = Path("/System/Library/Fonts/Supplemental/Futura.ttc")
MASTER = 2160
EDGE = 0.12  # half-width of the smoothing band, as a share of the black–yellow range


def smoothstep(x: np.ndarray, centre: float, half: float) -> np.ndarray:
    t = np.clip((x - (centre - half)) / (2 * half), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def crisp_master(size: int = MASTER) -> Image.Image:
    """The logo at `size`, every pixel black, yellow, or a narrow edge between them."""
    big = Image.open(SOURCE).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    a = np.asarray(big).astype(float)
    alpha = np.clip(a[..., 3] / 255.0, 1e-6, 1.0)
    rgb = a[..., :3] / alpha[..., None]  # undo the transparent edge's darkening
    # Where along black → yellow each pixel lies (luminance), then sharpened.
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    t = smoothstep(lum / float(YELLOW @ np.array([0.2126, 0.7152, 0.0722])), 0.5, EDGE)
    colour = t[..., None] * YELLOW
    sharp_alpha = smoothstep(a[..., 3] / 255.0, 0.5, EDGE)
    out = np.dstack([colour, sharp_alpha * 255.0]).round().clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def scaled(master: Image.Image, size: int) -> Image.Image:
    return master.resize((size, size), Image.Resampling.LANCZOS)


def on_ground(logo: Image.Image, width: int, height: int, top: int) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (*GROUND, 255))
    canvas.alpha_composite(logo, ((width - logo.width) // 2, top))
    return canvas


def centred_text(draw: ImageDraw.ImageDraw, width: int, y: int, text: str,
                 font: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> int:
    """Draw `text` centred at height `y`; return the y below it."""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text(((width - (right - left)) // 2 - left, y - top), text, font=font, fill=fill)
    return y + (bottom - top)


def poster(master: Image.Image) -> Image.Image:
    """9:16, 1440×2160: the logo, the name and its expansion."""
    width, height = 1440, 2160
    canvas = on_ground(scaled(master, 1120), width, height, top=330)
    draw = ImageDraw.Draw(canvas)
    name = ImageFont.truetype(str(FONT), 230, index=4)  # Futura Condensed ExtraBold
    small = ImageFont.truetype(str(FONT), 64, index=0)  # Futura Medium
    below = centred_text(draw, width, 1560, "V-Rex", name, tuple(int(c) for c in YELLOW))
    first = centred_text(draw, width, below + 70, "Vision Representation", small, TEXT_DIM)
    centred_text(draw, width, first + 28, "& Experimentation", small, TEXT_DIM)
    return canvas


def box_art(master: Image.Image) -> Image.Image:
    """1:1, 2160×2160: the logo on the dark ground."""
    logo = scaled(master, 1800)
    return on_ground(logo, MASTER, MASTER, top=(MASTER - logo.height) // 2)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    master = crisp_master()
    files = {
        "poster-art-1440x2160.png": poster(master).convert("RGB"),
        "box-art-2160x2160.png": box_art(master).convert("RGB"),
        "app-tile-icon-300x300.png": scaled(master, 300),
        "app-tile-icon-150x150.png": scaled(master, 150),
        "app-tile-icon-71x71.png": scaled(master, 71),
    }
    for name, image in files.items():
        image.save(OUT / name, optimize=True)
        print(f"{name}: {image.width}×{image.height}, {(OUT / name).stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
