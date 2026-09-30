"""Turning a video into image files a dataset can hold (doc 73).

**Why files at all.** Everything downstream of the Dataset Generator (the proposers, the
store, the trainer, COCO export) works on image paths. Decoding a video into files once is
what lets a video be a Generator source without teaching every one of those a second input
kind. The frames go inside the dataset's own directory, so they live and die with the
dataset they were annotated for.

**One pass, never a seek per frame.** `read_frame` decodes from the start each time (doc 68,
for exactness), which is right for one frame and quadratic for a range. Extraction walks
the stream once and keeps every `stride`-th frame from `start` on.

**JPEG, not PNG.** The source was lossy already; PNG spends two to three times the bytes on
detail the codec never recorded, and a 10-minute clip is 18,000 frames.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from app.core.paths import ensure_within
from app.ml.video.decode import VideoReadError, looks_like_video

logger = logging.getLogger(__name__)

JPEG_QUALITY = 92


@dataclass(frozen=True, slots=True)
class ExtractConfig:
    """Which frames of which video: every `stride`-th from `start`, `count` of them."""

    source: str
    start: int = 0
    count: int = 60
    stride: int = 1

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"start must not be negative: {self.start}")
        if self.count < 1:
            raise ValueError(f"count must be at least 1: {self.count}")
        if self.stride < 1:
            raise ValueError(f"stride must be at least 1: {self.stride}")
        if not looks_like_video(Path(self.source)):
            raise ValueError(f"Not a video file: {Path(self.source).name}")


def frames_dir(dataset_dir: Path, source: str) -> Path:
    """Where one video's frames go inside a dataset.

    Named by the video's stem *and* a hash of its full path: two videos called `run1.mp4`
    in different folders are different sources, and sharing a directory would let one's
    frame 12 overwrite the other's.
    """
    resolved = str(Path(source).expanduser().resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:8]
    root = dataset_dir / "frames"
    return ensure_within(root, root / f"{Path(source).stem}-{digest}")


def frame_filename(source: str, index: int) -> str:
    """Unique across videos, so a dataset that copies images cannot collide two frame 12s."""
    return f"{Path(source).stem}-f{index:06d}.jpg"


def extract_frames(
    config: ExtractConfig,
    destination: Path,
    on_frame: Callable[[int, str], None] = lambda _index, _path: None,
    cancelled: Callable[[], bool] = lambda: False,
) -> list[tuple[int, str]]:
    """Decode the chosen frames to JPEG files; return (source frame index, path) pairs.

    A frame already on disk is kept rather than rewritten, so extracting the same range
    twice (Change setup, then Start again) costs a decode and no writes.
    """
    import av

    path = Path(config.source).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"No such video: {config.source}")
    destination.mkdir(parents=True, exist_ok=True)

    written: list[tuple[int, str]] = []
    try:
        with av.open(str(path)) as container:
            if not container.streams.video:
                raise VideoReadError(f"No video stream in {path.name}")
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            for position, frame in enumerate(container.decode(stream)):
                if cancelled() or len(written) >= config.count:
                    break
                if position < config.start or (position - config.start) % config.stride:
                    continue
                target = destination / frame_filename(config.source, position)
                if not target.exists():
                    image = frame.to_image()  # type: ignore[no-untyped-call]
                    image.convert("RGB").save(target, "JPEG", quality=JPEG_QUALITY)
                written.append((position, str(target)))
                on_frame(position, str(target))
    except (VideoReadError, FileNotFoundError):
        raise
    except Exception as error:
        logger.info("Could not decode %s: %s", path.name, error)
        raise VideoReadError(f"Could not decode {path.name}") from error
    return written


@dataclass
class ExtractJob:
    """One extraction, its progress, and the frames it has written so far."""

    job_id: str
    config: ExtractConfig
    total: int
    state: str = "pending"
    message: str = ""
    frames: list[tuple[int, str]] = field(default_factory=list)
    cancel_requested: threading.Event = field(default_factory=threading.Event)

    @property
    def finished(self) -> bool:
        return self.state in {"complete", "failed", "cancelled"}


class FrameExtractor:
    """One extraction at a time: two would fight over the same disk and CPU."""

    def __init__(self) -> None:
        self._jobs: dict[str, ExtractJob] = {}
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="extract")

    def get(self, job_id: str) -> ExtractJob | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.finished:
            return False
        job.cancel_requested.set()
        return True

    def submit(self, config: ExtractConfig, destination: Path, available: int) -> ExtractJob:
        """`available` is the video's frame count, from a probe: it bounds the total."""
        if config.start >= available:
            raise ValueError(f"start {config.start} is past the last frame ({available - 1})")
        reachable = (available - config.start + config.stride - 1) // config.stride
        job = ExtractJob(uuid.uuid4().hex, config, total=min(config.count, reachable))
        self._jobs[job.job_id] = job
        self._pool.submit(self._run, job, destination)
        return job

    def _run(self, job: ExtractJob, destination: Path) -> None:
        job.state = "running"
        try:
            extract_frames(
                job.config,
                destination,
                on_frame=lambda index, path: job.frames.append((index, path)),
                cancelled=job.cancel_requested.is_set,
            )
        except Exception as error:  # noqa: BLE001 - surfaced on the job, logged with context
            logger.exception("Frame extraction %s failed", job.job_id)
            job.state, job.message = "failed", str(error)
            return
        job.state = "cancelled" if job.cancel_requested.is_set() else "complete"
        logger.info("Extracted %d frame(s) of %s", len(job.frames), job.config.source)


_extractor: FrameExtractor | None = None


def get_extractor() -> FrameExtractor:
    global _extractor
    if _extractor is None:
        _extractor = FrameExtractor()
    return _extractor


def reset_extractor() -> None:
    """Tests only: forget every job, so one test's extraction cannot leak into the next."""
    global _extractor
    _extractor = None


__all__ = [
    "ExtractConfig",
    "ExtractJob",
    "FrameExtractor",
    "extract_frames",
    "frame_filename",
    "frames_dir",
    "get_extractor",
    "reset_extractor",
]
