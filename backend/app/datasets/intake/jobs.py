"""Imports run in the background with progress (doc 136): a dataset of thousands of
pictures (OSDaR23, a YOLO export) takes minutes, longer than a request should wait."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from app.core.config import Settings
from app.datasets.intake.importer import ImportResult, run_import

logger = logging.getLogger(__name__)

State = Literal["running", "complete", "failed"]


@dataclass
class ImportJob:
    job_id: str
    path: str
    state: State = "running"
    done: int = 0
    total: int = 0
    current: str = ""
    result: ImportResult | None = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def report(self, done: int, total: int, current: str) -> None:
        with self._lock:
            self.done, self.total, self.current = done, max(total, done), current


class ImportJobs:
    def __init__(self) -> None:
        self._jobs: dict[str, ImportJob] = {}
        self._lock = threading.Lock()

    def get(self, job_id: str) -> ImportJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def submit(
        self,
        path: Path,
        name: str,
        description: str | None,
        copy_images: bool,
        settings: Settings | None = None,
    ) -> ImportJob:
        job = ImportJob(job_id=uuid.uuid4().hex, path=str(path))
        with self._lock:
            self._jobs[job.job_id] = job
        thread = threading.Thread(
            target=self._run,
            args=(job, path, name, description, copy_images, settings),
            name=f"import-{job.job_id[:8]}",
            daemon=True,
        )
        thread.start()
        return job

    @staticmethod
    def _run(
        job: ImportJob,
        path: Path,
        name: str,
        description: str | None,
        copy_images: bool,
        settings: Settings | None,
    ) -> None:
        try:
            job.result = run_import(path, name, description, copy_images, job.report, settings)
            job.state = "complete"
        except Exception as error:
            # A ValueError is the input's fault and its message is the explanation; anything
            # else is ours, logged with its traceback by run_import.
            logger.warning("Import %s of %s failed: %s", job.job_id, path, error)
            job.error = str(error) if isinstance(error, ValueError) else f"Import failed: {error}"
            job.state = "failed"


_jobs: ImportJobs | None = None


def get_import_jobs() -> ImportJobs:
    global _jobs
    if _jobs is None:
        _jobs = ImportJobs()
    return _jobs
