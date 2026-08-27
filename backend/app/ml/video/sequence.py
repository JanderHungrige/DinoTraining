"""One contract over a folder of images and a video file (doc 68).

A folder is already a frame sequence; a video becomes one by decoding. Behind
`FrameSequence` nothing downstream branches on which it is, which is the whole point — the
prepass runner, the frame route and the player are written once and work on both.

**The two differ in one honest way and it is exposed rather than hidden.** A folder has no
frame rate, so `fps` is `None` and the player picks one. Pretending a folder is 30 fps
would put a number on screen that came from nowhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.ml.images import FolderNotFoundError, list_images, read_image
from app.ml.video.decode import VideoInfo, VideoReadError, looks_like_video, probe, read_frame


@dataclass(frozen=True, slots=True)
class FrameSequence:
    """A finite, indexable run of frames.

    `paths` is populated for a folder and empty for a video: the prepass records which file
    each prediction came from, and for a folder that is a real path a user can open. A
    video frame has no path, and inventing one would be a filename that does not exist.
    """

    kind: str
    source: str
    frames: int
    fps: float | None
    width: int
    height: int
    paths: tuple[Path, ...] = ()

    @property
    def duration(self) -> float | None:
        """Seconds, when there is a frame rate to compute it from."""
        return None if not self.fps else self.frames / self.fps

    def label(self, index: int) -> str:
        """What to call frame ``index`` — its filename, or its position."""
        if self.paths and 0 <= index < len(self.paths):
            return self.paths[index].name
        return f"frame {index}"


def open_sequence(source: str) -> FrameSequence:
    """Resolve a folder or a video file into a sequence.

    Dispatches on what the path *is*, not on a flag the caller passes: a caller that has to
    say which kind it opened is a caller that can say the wrong one.
    """
    path = Path(source).expanduser()

    if path.is_dir():
        images = list_images(source)
        if not images:
            raise FolderNotFoundError(f"No images in {source}")
        # Size comes from the first frame. A folder whose images differ in size is not a
        # video and the player letterboxes each one anyway, so this is a hint for the
        # range control rather than a promise about every frame.
        first, _ = read_image(str(images[0]))
        return FrameSequence(
            kind="folder",
            source=source,
            frames=len(images),
            fps=None,
            width=first.width,
            height=first.height,
            paths=tuple(images),
        )

    if path.is_file() and looks_like_video(path):
        info: VideoInfo = probe(source)
        return FrameSequence(
            kind="video",
            source=source,
            frames=info.frames,
            fps=info.fps or None,
            width=info.width,
            height=info.height,
        )

    if path.is_file():
        raise VideoReadError(f"Not a video this app can play: {path.name}")
    raise FolderNotFoundError(f"Not a folder or a video: {source}")


def frame_image(sequence: FrameSequence, index: int) -> Image.Image:
    """One frame as RGB.

    Range-checked here rather than trusted from the request: a video decoder asked for
    frame 10^9 walks the whole file before failing, which is a request that never returns
    rather than an error.
    """
    if not 0 <= index < sequence.frames:
        raise IndexError(f"Frame {index} is outside 0..{sequence.frames - 1}")

    if sequence.kind == "folder":
        image, _ = read_image(str(sequence.paths[index]))
        return image
    return read_frame(sequence.source, index)


def frame_range(sequence: FrameSequence, start: int, count: int) -> range:
    """The frames a run will actually cover, clamped to what exists.

    Clamped rather than refused. Asking for 200 frames from frame 300 of a 350-frame video
    is not a mistake worth an error — it is someone asking for "the rest", and answering
    with the rest is what they meant.
    """
    if start < 0:
        raise ValueError(f"start must not be negative: {start}")
    if count < 1:
        raise ValueError(f"count must be at least 1: {count}")
    if start >= sequence.frames:
        raise ValueError(f"start {start} is past the last frame ({sequence.frames - 1})")
    return range(start, min(start + count, sequence.frames))


__all__ = ["FrameSequence", "frame_image", "frame_range", "open_sequence"]
