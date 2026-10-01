"""Imports run in the background with progress (doc 136): a dataset of thousands of
pictures (OSDaR23, a YOLO export) takes minutes, longer than a request should wait."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from app.core.config import Settings
from app.datasets.examples.catalogue import Example, Variant, dataset_name, description
from app.datasets.examples.fetch import Chunks, fetch, http_chunks
from app.datasets.intake.importer import ImportResult, run_import

logger = logging.getLogger(__name__)

State = Literal["running", "complete", "failed"]
#: An example (doc 138) downloads first; progress is in bytes then, in pictures after.
Phase = Literal["download", "import"]


@dataclass
class ImportJob:
    job_id: str
    path: str
    state: State = "running"
    phase: Phase = "import"
    #: "<example>/<variant>" for an example, so a second click joins the running job.
    example: str | None = None
    done: int = 0
    total: int = 0
    current: str = ""
    result: ImportResult | None = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def report(self, done: int, total: int, current: str) -> None:
        with self._lock:
            self.done, self.total, self.current = done, max(total, done), current

    def enter(self, phase: Phase) -> None:
        with self._lock:
            self.phase, self.done, self.total, self.current = phase, 0, 0, ""


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

        def work() -> ImportResult:
            return run_import(path, name, description, copy_images, job.report, settings)

        return self._start(job, work)

    def running_example(self, example_id: str) -> ImportJob | None:
        """The example's download or import still running, for a page opened later."""
        with self._lock:
            for job in self._jobs.values():
                if job.state == "running" and (job.example or "").startswith(example_id + "/"):
                    return job
        return None

    def submit_example(
        self,
        example: Example,
        variant: Variant,
        settings: Settings | None = None,
        chunks: Chunks = http_chunks,
    ) -> ImportJob:
        """Download (unless already there), then import in place (doc 138)."""
        key = f"{example.example_id}/{variant}"
        with self._lock:
            for running in self._jobs.values():
                if running.example == key and running.state == "running":
                    return running
        job = ImportJob(job_id=uuid.uuid4().hex, path=example.url, phase="download", example=key)

        def work() -> ImportResult:
            folder = fetch(example, variant, job.report, settings, chunks)
            job.path = str(folder)
            job.enter("import")
            name, text = dataset_name(example, variant), description(example, variant)
            return run_import(folder, name, text, False, job.report, settings)

        return self._start(job, work)

    def submit_link(
        self, link_id: str, name: str, description: str | None, settings: Settings | None = None
    ) -> ImportJob:
        """Doc 148: list the bucket (again, if needed), then import without the pictures."""
        from app.cloud.linking import import_link  # the cloud package imports this module's kin

        job = ImportJob(job_id=uuid.uuid4().hex, path=link_id)

        def work() -> ImportResult:
            return import_link(link_id, name, description, job.report, settings)

        return self._start(job, work)

    def _start(self, job: ImportJob, work: Callable[[], ImportResult]) -> ImportJob:
        with self._lock:
            self._jobs[job.job_id] = job
        thread = threading.Thread(
            target=self._run, args=(job, work), name=f"import-{job.job_id[:8]}", daemon=True
        )
        thread.start()
        return job

    @staticmethod
    def _run(job: ImportJob, work: Callable[[], ImportResult]) -> None:
        try:
            job.result = work()
            job.state = "complete"
        except Exception as error:
            # A ValueError is the input's fault and its message is the explanation; anything
            # else is ours, and its traceback goes to the log.
            if isinstance(error, ValueError):
                logger.warning("Import %s of %s failed: %s", job.job_id, job.path, error)
            else:
                logger.exception("Import %s of %s failed", job.job_id, job.path)
            job.error = str(error) if isinstance(error, ValueError) else f"Import failed: {error}"
            job.state = "failed"


_jobs: ImportJobs | None = None


def get_import_jobs() -> ImportJobs:
    global _jobs
    if _jobs is None:
        _jobs = ImportJobs()
    return _jobs
