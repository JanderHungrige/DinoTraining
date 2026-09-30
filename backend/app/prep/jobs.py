"""A small job runner for data-preparation work (docs 81, 84, 89).

An audit opens every image and hashes it; on a few thousand images that is longer than a
request should take. One worker, like the other runners here: two audits at once would
fight over the same disk and both would take longer.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

Progress = Callable[[int, int], None]


@dataclass
class PrepJob:
    job_id: str
    kind: str
    state: str = "pending"
    done: int = 0
    total: int = 0
    message: str = ""
    result: Any = None
    cancel_requested: threading.Event = field(default_factory=threading.Event)

    @property
    def finished(self) -> bool:
        return self.state in {"complete", "failed", "cancelled"}


class PrepRunner:
    def __init__(self) -> None:
        self._jobs: dict[str, PrepJob] = {}
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="prep")

    def get(self, job_id: str) -> PrepJob | None:
        return self._jobs.get(job_id)

    def submit(self, kind: str, work: Callable[[PrepJob, Progress], Any]) -> PrepJob:
        job = PrepJob(job_id=uuid.uuid4().hex, kind=kind)
        self._jobs[job.job_id] = job

        def progress(done: int, total: int) -> None:
            job.done, job.total = done, total

        def run() -> None:
            job.state = "running"
            try:
                job.result = work(job, progress)
            except Exception as error:  # noqa: BLE001 - surfaced on the job, logged here
                logger.exception("Preparation job %s (%s) failed", job.job_id, kind)
                job.state, job.message = "failed", str(error)
                return
            job.state = "cancelled" if job.cancel_requested.is_set() else "complete"

        self._pool.submit(run)
        return job


_runner: PrepRunner | None = None


def get_prep_runner() -> PrepRunner:
    global _runner
    if _runner is None:
        _runner = PrepRunner()
    return _runner


def reset_prep_runner() -> None:
    """Tests only."""
    global _runner
    _runner = None


__all__ = ["PrepJob", "PrepRunner", "Progress", "get_prep_runner", "reset_prep_runner"]
