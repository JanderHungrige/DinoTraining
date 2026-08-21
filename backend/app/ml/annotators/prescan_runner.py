"""Running a prescan as a job (doc 53).

Mirrors `finetune_runner.py`'s shape — submit, poll, cancel — for the same reason it mirrors
`training/runner.py`'s: the UI already knows how to watch a job. It is a separate runner
rather than a reuse because the loops share nothing except that shape.

Scanning four hundred frames is minutes, so it cannot be a request. It also cannot be *one*
worker shared with training: a prescan that queues behind a six-minute fine-tune looks hung.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace

from app.core.config import Settings, get_settings
from app.ml.annotators.prescan import PrescanConfig, PrescanHit, propose_for, scan_boxes
from app.ml.images import ImageReadError, read_image
from app.ml.training.job import JobState

logger = logging.getLogger(__name__)


class _Unreadable(Exception):
    """One image could not be opened. Counted, not fatal — a folder of four hundred frames
    with one truncated PNG must not lose the other three hundred and ninety-nine."""


@dataclass
class PrescanJob:
    """Live state of one scan. Mutated by the worker, read by the API."""

    job_id: str
    config: PrescanConfig
    state: JobState = "pending"
    scanned: int = 0
    total: int = 0
    unreadable: int = 0
    hits: list[PrescanHit] = field(default_factory=list)
    message: str = ""
    cancel_requested: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_unreadable(self) -> None:
        with self._lock:
            self.scanned += 1
            self.unreadable += 1

    def record(self, hit: PrescanHit | None) -> None:
        with self._lock:
            self.scanned += 1
            if hit is not None:
                self.hits.append(hit)

    def finish(self, state: JobState, message: str = "") -> None:
        with self._lock:
            self.state = state
            self.message = message

    @property
    def finished(self) -> bool:
        return self.state in {"complete", "failed", "cancelled"}

    def snapshot(self) -> tuple[int, int, list[PrescanHit]]:
        """A consistent read of the three fields the UI shows together.

        Read one at a time they can disagree — 8 scanned with 9 hits — which reads as a
        counting bug rather than as a race.
        """
        with self._lock:
            return self.scanned, self.unreadable, list(self.hits)


class PrescanRunner:
    """One scan at a time, on its own worker."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._jobs: dict[str, PrescanJob] = {}
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="prescan")

    def get(self, job_id: str) -> PrescanJob | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.finished:
            return False
        job.cancel_requested.set()
        return True

    def submit(self, config: PrescanConfig) -> PrescanJob:
        job = PrescanJob(
            job_id=uuid.uuid4().hex, config=config, total=len(config.image_paths)
        )
        self._jobs[job.job_id] = job
        self._pool.submit(self._run, job)
        return job

    def _run(self, job: PrescanJob) -> None:
        try:
            job.state = "running"
            self._scan(job)
        except Exception as exc:  # noqa: BLE001 - surfaced on the job, logged with context
            logger.exception("Prescan job %s failed", job.job_id)
            job.finish("failed", str(exc))

    def _scan(self, job: PrescanJob) -> None:
        config = job.config
        for path in config.image_paths:
            if job.cancel_requested.is_set():
                # A cancelled scan keeps the hits it found. The user asked it to stop, not
                # to throw away the answer it had already reached.
                job.finish("cancelled", f"Stopped after {job.scanned} of {job.total}")
                return
            try:
                job.record(self._scan_one(path, config))
            except _Unreadable:
                job.record_unreadable()

        logger.info(
            "Prescan %s: %d of %d image(s) matched %s",
            job.job_id,
            len(job.hits),
            job.total,
            config.labels or ("anything",),
        )
        job.finish("complete")

    def _scan_one(self, path: str, config: PrescanConfig) -> PrescanHit | None:
        """One image, or `_Unreadable` if it will not open.

        The unreadable count is reported, so a scan that quietly read almost nothing cannot
        pass for a scan that found almost nothing.
        """
        try:
            image, _ = read_image(path)
        except (OSError, ImageReadError):
            logger.warning("Prescan could not read %s", path)
            raise _Unreadable from None

        hit = scan_boxes(propose_for(image, config, self._settings), config)
        return None if hit is None else replace(hit, path=path)


_RUNNER: PrescanRunner | None = None


def get_prescan_runner() -> PrescanRunner:
    global _RUNNER  # noqa: PLW0603 - one process-wide runner, as the other runners have
    if _RUNNER is None:
        _RUNNER = PrescanRunner()
    return _RUNNER


__all__ = ["PrescanJob", "PrescanRunner", "get_prescan_runner"]
