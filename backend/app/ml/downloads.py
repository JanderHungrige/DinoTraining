"""Download manager for model weights.

``snapshot_download`` is blocking, so downloads run in a worker thread and report
progress into an in-memory job table. Jobs are intentionally not persisted: HF's own
cache resumes an interrupted transfer, and a "downloading" row that survived a restart
would describe a thread that no longer exists.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from app.ml.registry import ModelSpec

logger = logging.getLogger(__name__)

JobState = Literal["pending", "downloading", "complete", "failed"]


@dataclass
class DownloadJob:
    """Progress record for one model download."""

    job_id: str
    model_id: str
    state: JobState = "pending"
    downloaded_bytes: int = 0
    total_bytes: int = 0
    message: str = ""
    # Absolute position per progress bar, keyed by bar identity. snapshot_download
    # runs one bar per file concurrently; accumulating their deltas against a single
    # bar's total is what produced a cheerful "194%" the first time round.
    _bars: dict[int, tuple[int, int]] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def report_bar(self, bar_id: int, current: int, total: int) -> None:
        """Record one bar's absolute position and recompute the aggregate."""
        with self._lock:
            self._bars[bar_id] = (max(current, 0), max(total, 0))
            self.downloaded_bytes = sum(current for current, _ in self._bars.values())
            self.total_bytes = sum(total for _, total in self._bars.values())

    def finish(self, state: JobState, message: str = "") -> None:
        with self._lock:
            self.state = state
            self.message = message
            if state == "complete" and self.total_bytes:
                # Never leave a completed job reading 97% because a bar closed early.
                self.downloaded_bytes = self.total_bytes


def _make_tqdm_class(job: DownloadJob) -> type:
    """Build a tqdm subclass that reports into ``job``.

    huggingface_hub drives progress through tqdm, so subclassing it is the supported
    way to observe byte counts without reimplementing the download.
    """
    from tqdm.auto import tqdm as base_tqdm

    class JobTqdm(base_tqdm):  # type: ignore[misc]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            # HF marks byte transfers with unit="B"; the "Fetching N files" bar counts
            # files. Summing both would add apples to bytes.
            self._tracks_bytes = kwargs.get("unit") == "B"

        def _report(self) -> None:
            if self._tracks_bytes:
                job.report_bar(id(self), int(self.n or 0), int(self.total or 0))

        def update(self, n: float | None = 1) -> bool | None:
            result: bool | None = super().update(n)
            self._report()
            return result

        def close(self) -> None:
            # A bar can finish without a final update; capture its end state.
            self._report()
            super().close()

    return JobTqdm


class DownloadManager:
    """Tracks download jobs. One instance per process."""

    def __init__(self) -> None:
        self._jobs: dict[str, DownloadJob] = {}
        self._by_model: dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, job_id: str) -> DownloadJob | None:
        return self._jobs.get(job_id)

    def active_for(self, model_id: str) -> DownloadJob | None:
        """The in-flight job for a model, if any."""
        with self._lock:
            job_id = self._by_model.get(model_id)
        job = self._jobs.get(job_id) if job_id else None
        if job and job.state in ("pending", "downloading"):
            return job
        return None

    def start(self, spec: ModelSpec, target_dir: Path, token: str | None) -> DownloadJob:
        """Register a job and kick off the download in a worker thread."""
        job = DownloadJob(job_id=uuid.uuid4().hex, model_id=spec.id)
        with self._lock:
            self._jobs[job.job_id] = job
            self._by_model[spec.id] = job.job_id

        asyncio.get_running_loop().create_task(self._run(job, spec, target_dir, token))
        return job

    async def _run(
        self, job: DownloadJob, spec: ModelSpec, target_dir: Path, token: str | None
    ) -> None:
        job.state = "downloading"
        try:
            await asyncio.to_thread(_download, job, spec, target_dir, token)
        except Exception as error:  # noqa: BLE001 - reported to the user, then logged
            # Log with context, report the class rather than the text: HF errors can
            # embed the request URL, and a token can ride along in it.
            logger.exception("Download failed for %s", spec.id)
            job.finish("failed", f"{type(error).__name__} while downloading {spec.repo_id}")
            return
        job.finish("complete")
        logger.info("Download complete for %s", spec.id)


def _download(job: DownloadJob, spec: ModelSpec, target_dir: Path, token: str | None) -> None:
    """Blocking download body. Runs on a worker thread."""
    from huggingface_hub import snapshot_download

    target_dir.mkdir(parents=True, exist_ok=True)
    kwargs: dict[str, Any] = {
        "repo_id": spec.repo_id,
        "local_dir": str(target_dir),
        "tqdm_class": _make_tqdm_class(job),
    }
    if token:
        kwargs["token"] = token
    snapshot_download(**kwargs)


_manager = DownloadManager()


def get_download_manager() -> DownloadManager:
    """The process-wide download manager."""
    return _manager
