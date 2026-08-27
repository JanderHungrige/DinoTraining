"""The prepass: run the chosen models over a frame range, once (doc 68).

**Why this is a job and not a request.** Measured on this machine: Grounded SAM ~5 s per
frame, RF-DETR ~0.1 s, a DINOv2 head ~0.2 s. A 120-frame range is minutes, and playback
cannot wait on inference anyway — the frame on screen would arrive after the frame it
describes. So the models run first, into a cache, and the player reads that.

**This is `PrescanRunner` again, on purpose.** Doc 53 already runs a model over many images
with progress, cancellation and polling, and the job mechanics here follow it rather than
being reinvented. What differs is the answer: prescan asks "which images contain X" and
discards the predictions; this keeps every one and asks nothing.

**Each frame is an ordinary `run_heads` call.** There is no second inference path. A
sequence run over one frame must produce exactly what the single-image viewer produces for
that frame, or the two surfaces will disagree and only one of them will be believed.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.core.config import Settings, get_settings
from app.ml.foundation.build import build_foundation
from app.ml.foundation.run import predict_with
from app.ml.inference.compose import run_heads
from app.ml.inference.engine import DEFAULT_SCORE_THRESHOLD
from app.ml.inference.results import Prediction
from app.ml.video.sequence import FrameSequence, frame_image, frame_range

logger = logging.getLogger(__name__)

JobState = str


@dataclass(frozen=True, slots=True)
class SequenceRunConfig:
    """What to run, over which frames."""

    source: str
    start: int
    count: int
    backbone_id: str = ""
    instance_ids: tuple[str, ...] = ()
    foundation_ids: tuple[str, ...] = ()
    concept: str = ""
    score_threshold: float = DEFAULT_SCORE_THRESHOLD

    def __post_init__(self) -> None:
        if not self.instance_ids and not self.foundation_ids:
            raise ValueError("Select at least one head or foundation model to run")
        if self.instance_ids and not self.backbone_id:
            raise ValueError("Heads need a backbone to run on")


@dataclass
class SequenceRun:
    """One prepass, its progress, and the predictions it has produced so far."""

    job_id: str
    config: SequenceRunConfig
    total: int
    state: JobState = "pending"
    done: int = 0
    unreadable: int = 0
    message: str = ""
    #: Frame index -> the predictions for that frame. Sparse until the run finishes, which
    #: is what lets the player start watching the beginning while the end is still running.
    frames: dict[int, list[Prediction]] = field(default_factory=dict)
    cancel_requested: threading.Event = field(default_factory=threading.Event)

    @property
    def finished(self) -> bool:
        return self.state in {"complete", "failed", "cancelled"}

    def finish(self, state: JobState, message: str = "") -> None:
        self.state = state
        self.message = message


class SequenceRunner:
    """One prepass at a time, on its own worker.

    Single worker deliberately: two runs would compete for the same GPU and both would
    take longer than either alone, while the progress bars each claimed to be moving.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._runs: dict[str, SequenceRun] = {}
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sequence")

    def get(self, job_id: str) -> SequenceRun | None:
        return self._runs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        run = self._runs.get(job_id)
        if run is None or run.finished:
            return False
        run.cancel_requested.set()
        return True

    def submit(self, sequence: FrameSequence, config: SequenceRunConfig) -> SequenceRun:
        indices = frame_range(sequence, config.start, config.count)
        run = SequenceRun(job_id=uuid.uuid4().hex, config=config, total=len(indices))
        self._runs[run.job_id] = run
        self._pool.submit(self._run, run, sequence, indices)
        return run

    def _run(self, run: SequenceRun, sequence: FrameSequence, indices: range) -> None:
        try:
            run.state = "running"
            self._walk(run, sequence, indices)
        except Exception as exc:  # noqa: BLE001 - surfaced on the job, logged with context
            logger.exception("Sequence run %s failed", run.job_id)
            run.finish("failed", str(exc))

    def _walk(self, run: SequenceRun, sequence: FrameSequence, indices: range) -> None:
        started = time.perf_counter()

        for index in indices:
            if run.cancel_requested.is_set():
                # A cancelled run keeps the frames it finished. The user asked it to stop,
                # not to throw away the part they can already watch.
                run.finish("cancelled", f"Stopped after {run.done} of {run.total} frames")
                return
            try:
                run.frames[index] = self._one_frame(sequence, index, run.config)
            except Exception as error:  # noqa: BLE001 - one bad frame must not end the run
                logger.warning("Frame %d of %s: %s", index, sequence.source, error)
                run.unreadable += 1
            run.done += 1

        elapsed = time.perf_counter() - started
        logger.info(
            "Sequence run %s: %d frame(s) in %.1fs (%d unreadable)",
            run.job_id,
            run.done,
            elapsed,
            run.unreadable,
        )
        # Reported rather than swallowed: a run that read almost nothing must not pass for
        # a run that found almost nothing.
        run.finish(
            "complete",
            f"{run.unreadable} frame(s) could not be read" if run.unreadable else "",
        )

    def _one_frame(
        self, sequence: FrameSequence, index: int, config: SequenceRunConfig
    ) -> list[Prediction]:
        """Every model, over one frame. The same call the single-image viewer makes."""
        image = frame_image(sequence, index)
        predictions: list[Prediction] = []

        if config.instance_ids:
            composed = run_heads(
                image,
                config.backbone_id,
                list(config.instance_ids),
                self._settings,
                config.score_threshold,
            )
            predictions.extend(composed.predictions)

        for foundation_id in config.foundation_ids:
            model = build_foundation(foundation_id, self._settings)
            predictions.append(
                predict_with(model, image, config.concept, config.score_threshold)
            )

        return predictions

_runner: SequenceRunner | None = None


def get_runner(settings: Settings | None = None) -> SequenceRunner:
    """The process-wide runner. One, so two prepasses cannot fight over the GPU."""
    global _runner
    if _runner is None:
        _runner = SequenceRunner(settings)
    return _runner


def reset_runner() -> None:
    """Drop the runner. For tests, and for a settings change that moves the data root."""
    global _runner
    _runner = None


__all__ = [
    "SequenceRun",
    "SequenceRunConfig",
    "SequenceRunner",
    "get_runner",
    "reset_runner",
]
