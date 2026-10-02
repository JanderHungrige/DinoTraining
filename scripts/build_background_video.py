"""Build the app's former background loop from the Pixabay source clip (doc 76).

Since 2026-10-02 the background is a Pexels forest, built with the ffmpeg commands in
``apps/frontend/public/background/PROVENANCE.md``; this script rebuilds the old loop only.

    backend/.venv/bin/python scripts/build_background_video.py [--source PATH]

Mirror-stitches the clip (frames 0…N-1, then N-2…1) so the last frame leads straight back
into the first and the loop has no seam, downscales it, and encodes a small H.264 file plus
a poster frame into ``apps/frontend/public/background/``.

**Frames are spooled to disk, never held.** ``ffmpeg -vf reverse`` keeps every frame in
memory, which for 870 frames of 1080p is several gigabytes. Decoding once, scaling each
frame as it arrives and writing it to a temporary JPEG keeps memory flat whatever the
clip's length.

The source is not committed (it is 13 MB and the Pixabay licence does not allow shipping
the file on its own). Without ``--source``, it is fetched by URL and checked against its
sha256, so the committed loop can always be rebuilt from the same bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import urllib.request
from pathlib import Path

SOURCE_URL = "https://cdn.pixabay.com/video/2016/09/13/5192-183786490_large.mp4"
SOURCE_SHA256 = "233e123d9e5c25c1b7ca375ef0db6760be235ae4b5c135ea52b1a1f02de73349"
OUT_DIR = Path(__file__).resolve().parents[1] / "apps" / "frontend" / "public" / "background"
LOOP_NAME = "particles-loop.mp4"
POSTER_NAME = "particles-poster.jpg"


def mirror_order(count: int) -> list[int]:
    """Forwards, then backwards without repeating either turn-around frame.

    A frame shown twice in a row is a visible stall at 30 fps: once at the far end (N-1
    would follow N-1) and once at the seam (0 would follow 0 as the loop restarts).
    """
    if count < 2:
        return list(range(count))
    return list(range(count)) + list(range(count - 2, 0, -1))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_source(target: Path) -> Path:
    urllib.request.urlretrieve(SOURCE_URL, target)
    actual = sha256_of(target)
    if actual != SOURCE_SHA256:
        raise SystemExit(f"Source sha256 is {actual}, expected {SOURCE_SHA256}; refusing to build")
    return target


def spool_frames(source: Path, spool: Path, width: int) -> tuple[int, float, tuple[int, int]]:
    """Decode once, scale each frame, write it as a JPEG. Returns count, fps and size."""
    import av

    count = 0
    with av.open(str(source)) as container:
        stream = container.streams.video[0]
        fps = float(stream.average_rate or 30)
        size = (0, 0)
        for frame in container.decode(stream):
            image = frame.to_image()  # type: ignore[no-untyped-call]
            height = round(image.height * width / image.width / 2) * 2  # even, for yuv420p
            image = image.convert("RGB").resize((width, height))
            image.save(spool / f"{count:05d}.jpg", "JPEG", quality=95)
            size = (width, height)
            count += 1
    return count, fps, size


def encode(spool: Path, order: list[int], fps: float, size: tuple[int, int], crf: int, out: Path) -> None:
    import av
    from PIL import Image

    with av.open(str(out), mode="w", options={"movflags": "+faststart"}) as container:
        stream = container.add_stream("libx264", rate=round(fps))
        stream.width, stream.height = size
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": str(crf), "preset": "slow", "profile": "main", "tune": "film"}
        for index in order:
            with Image.open(spool / f"{index:05d}.jpg") as image:
                frame = av.VideoFrame.from_image(image.convert("RGB"))
            container.mux(stream.encode(frame))
        container.mux(stream.encode(None))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, help="Local copy of the Pixabay clip")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--crf", type=int, default=30)
    parser.add_argument("--budget-mb", type=float, default=8.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        source = args.source or fetch_source(Path(scratch) / "source.mp4")
        if sha256_of(source) != SOURCE_SHA256:
            print(f"warning: {source} is not the recorded Pixabay file", file=sys.stderr)
        spool = Path(scratch) / "frames"
        spool.mkdir()
        count, fps, size = spool_frames(source, spool, args.width)
        order = mirror_order(count)
        out = OUT_DIR / LOOP_NAME
        encode(spool, order, fps, size, args.crf, out)
        (spool / "00000.jpg").rename(OUT_DIR / POSTER_NAME)

    megabytes = out.stat().st_size / 1e6
    print(f"{out.name}: {len(order)} frames ({count} source), {size[0]}x{size[1]}, "
          f"{len(order) / fps:.1f} s, {megabytes:.2f} MB")
    if megabytes > args.budget_mb:
        print(f"over the {args.budget_mb} MB budget — raise --crf or lower --width", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
