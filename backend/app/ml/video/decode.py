"""Reading frames out of a video file (doc 68).

**PyAV rather than opencv or imageio**, because its wheels bundle the ffmpeg libraries and
playback therefore does not become a system-ffmpeg prerequisite the installer cannot
satisfy. torchvision was checked first and is not an option: its video APIs were removed
before 0.28, the version this app pins.

Two operations, and they are deliberately the only two. `probe` answers *how many frames
and how fast*; `read_frame` answers *give me frame N*. Nothing here returns a stream or
holds a decoder open between requests, because a 300-frame 2464x1600 sequence is ~3.5 GB as
raw RGB and the one thing this module must never do is decide to keep that.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

#: Containers worth offering. Deliberately short: every one of these is something a camera
#: or a screen recorder actually writes, and a longer list is a longer list of ways to
#: discover at decode time that ffmpeg was built without the codec.
VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"})


class VideoReadError(ValueError):
    """The path is not a readable video."""


@dataclass(frozen=True, slots=True)
class VideoInfo:
    """What a player needs before it can offer a range."""

    frames: int
    fps: float
    width: int
    height: int
    #: Seconds. Derived rather than read, so it always agrees with `frames` and `fps`.
    duration: float


def looks_like_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_SUFFIXES


def probe(path_str: str) -> VideoInfo:
    """Frame count, rate and size for a video file.

    **The frame count is counted when the container does not know it.** `stream.frames` is
    0 for a good number of real files — anything written as a fragmented MP4, and most
    webm — and returning 0 would tell the player the video is empty. Counting means
    demuxing every packet once, which is far cheaper than decoding them and happens once
    per file rather than once per request.
    """
    import av

    path = Path(path_str).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"No such video: {path_str}")

    try:
        with av.open(str(path)) as container:
            if not container.streams.video:
                raise VideoReadError(f"No video stream in {path.name}")
            stream = container.streams.video[0]
            width = int(stream.codec_context.width)
            height = int(stream.codec_context.height)
            rate = stream.average_rate or stream.guessed_rate
            fps = float(rate) if rate else 0.0
            frames = int(stream.frames or 0)
            if frames <= 0:
                frames = sum(1 for _ in container.demux(stream) if not _.is_corrupt)
    except VideoReadError:
        raise
    except Exception as error:  # av raises its own hierarchy; treat any of it as unreadable
        logger.info("Could not probe %s: %s", path.name, error)
        raise VideoReadError(f"Could not read video: {path.name}") from error

    if frames <= 0 or width <= 0 or height <= 0:
        raise VideoReadError(f"{path.name} reports no frames")

    return VideoInfo(
        frames=frames,
        fps=fps,
        width=width,
        height=height,
        duration=frames / fps if fps > 0 else 0.0,
    )


def read_frame(path_str: str, index: int) -> Image.Image:
    """Frame ``index`` as RGB, counting from zero.

    **Decoded from the start rather than seeked.** Seeking lands on the nearest keyframe and
    the frame that comes back is *near* the one asked for, not the one asked for — which is
    invisible until an overlay computed for frame 210 is drawn over frame 207 and the boxes
    trail the object by three frames. Doc 68 exists to make the picture and the prediction
    the same frame; a fast approximate seek would give that away for smoothness nobody
    asked for.

    Linear decoding is fine for the two things this serves — a sequential prepass and
    playback, both of which walk forward — and is the honest cost of exactness.
    """
    import av

    if index < 0:
        raise VideoReadError(f"Frame index must not be negative: {index}")

    path = Path(path_str).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"No such video: {path_str}")

    try:
        with av.open(str(path)) as container:
            if not container.streams.video:
                raise VideoReadError(f"No video stream in {path.name}")
            stream = container.streams.video[0]
            # Let PyAV use every core it has; a 4K frame is otherwise slow enough to feel.
            stream.thread_type = "AUTO"
            for position, frame in enumerate(container.decode(stream)):
                if position == index:
                    # PyAV ships no stubs for `to_image`, so this edge is untyped; the
                    # convert() below is what actually guarantees the mode.
                    decoded = frame.to_image()  # type: ignore[no-untyped-call]
                    converted: Image.Image = decoded.convert("RGB")
                    return converted
    except VideoReadError:
        raise
    except Exception as error:
        logger.info("Could not decode frame %d of %s: %s", index, path.name, error)
        raise VideoReadError(f"Could not decode frame {index}: {path.name}") from error

    raise VideoReadError(f"{path.name} has no frame {index}")


__all__ = [
    "VIDEO_SUFFIXES",
    "VideoInfo",
    "VideoReadError",
    "looks_like_video",
    "probe",
    "read_frame",
]
