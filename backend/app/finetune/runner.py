"""One job lifecycle for every fine-tunable model (doc 93).

Submit runs the preflight (doc 92) and refuses in its words before anything loads. A run
then scores the **base** model on the held-out pictures, trains, keeps the best epoch by
validation, and scores that on the same held-out pictures, so "fine-tuning helped" is a
number, not a feeling. The best epoch's weights are kept in memory and saved once, at the
end, after the comparison; a cancelled run saves nothing (doc 44's runner, which saved on
every improvement, remains for the RF-DETR panel until doc 97 moves it here).
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.core.config import Settings, get_settings
from app.finetune.adapter import FinetuneAdapter, FinetuneData, FinetuneSettings, TrainingState
from app.finetune.adapters import get_adapter
from app.finetune.data import load_data
from app.finetune.preflight import preflight, refusal
from app.finetune.requirements import get_requirements
from app.ml.foundation.instances import FoundationInstanceStore
from app.ml.training.job import JobState

logger = logging.getLogger(__name__)

#: The base model, as the best "epoch" nothing beat.
BASE = object()


class FinetuneRefusedError(ValueError):
    """The dataset does not meet the model's requirements; the message says which."""


@dataclass
class FinetuneRequest:
    finetune_id: str
    dataset_ids: tuple[str, ...]
    name: str
    recipe_id: str | None = None
    settings: FinetuneSettings = field(default_factory=FinetuneSettings)


@dataclass
class EpochResult:
    epoch: int
    train_loss: float
    metrics: dict[str, float]


@dataclass
class FoundationFinetuneJob:
    job_id: str
    request: FinetuneRequest
    state: JobState = "pending"
    epoch: int = 0
    history: list[EpochResult] = field(default_factory=list)
    primary_metric: str = ""
    best_metric: float | None = None
    #: 0 when the base model stayed best.
    best_epoch: int = 0
    #: The base and the fine-tuned model on the same held-out pictures.
    baseline_metrics: dict[str, float] = field(default_factory=dict)
    final_metrics: dict[str, float] = field(default_factory=dict)
    held_out: str = ""
    notes: list[str] = field(default_factory=list)
    message: str = ""
    instance_id: str | None = None
    cancel_requested: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def finished(self) -> bool:
        return self.state in {"complete", "failed", "cancelled"}


class FoundationFinetuneRunner:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._jobs: dict[str, FoundationFinetuneJob] = {}
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="foundation-finetune")

    def list_all(self) -> list[FoundationFinetuneJob]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> FoundationFinetuneJob | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.finished:
            return False
        job.cancel_requested.set()
        return True

    def submit(self, request: FinetuneRequest) -> FoundationFinetuneJob:
        """Refuses (FinetuneRefusedError) when the preflight fails, before any work."""
        for dataset_id in request.dataset_ids:
            readiness = preflight(
                request.finetune_id, dataset_id, request.recipe_id, self._settings
            )
            if not readiness.ready:
                raise FinetuneRefusedError(refusal(readiness))
        job = FoundationFinetuneJob(job_id=uuid.uuid4().hex, request=request)
        self._jobs[job.job_id] = job
        self._pool.submit(self._run, job)
        return job

    def _run(self, job: FoundationFinetuneJob) -> None:
        try:
            job.state = "running"
            self._train(job)
        except Exception as exc:  # noqa: BLE001 - surfaced on the job, logged with context
            logger.exception("Foundation fine-tune %s failed", job.job_id)
            job.state, job.message = "failed", str(exc)

    def _train(self, job: FoundationFinetuneJob) -> None:
        request = job.request
        adapter = get_adapter(request.finetune_id)
        job.primary_metric = adapter.primary_metric
        spec = get_requirements(request.finetune_id)
        data = load_data(
            spec, request.dataset_ids, request.recipe_id, request.settings.seed, self._settings
        )
        job.held_out = "test" if data.test else "validation"
        if not data.test:
            job.notes.append(
                "No test pictures: base and fine-tuned are compared on the validation side, "
                "which also picked the best epoch, so the gain is optimistic."
            )
        state = adapter.prepare(data, request.settings, self._settings)
        # A fair baseline where the adapter knows one (doc 95: a head on the frozen
        # backbone); otherwise the base model as it is.
        baseline = getattr(adapter, "baseline", None)
        job.baseline_metrics = (
            baseline(data, request.settings, self._settings)
            if baseline
            else adapter.evaluate(state, data.held_out)
        )
        base_val = adapter.evaluate(state, data.val) if data.val else {}
        job.best_metric = base_val.get(adapter.primary_metric)
        best = self._epochs(job, adapter, state, data)
        if best is None:
            return
        if best is BASE:
            self._base_kept(job, base_val.get(adapter.primary_metric))
            return
        adapter.restore(state, best)
        job.final_metrics = adapter.evaluate(state, data.held_out)
        self._compare(job)
        self._save(job, adapter, state, data)
        job.state, job.message = "complete", f"Finished {job.epoch} epochs"

    def _epochs(
        self,
        job: FoundationFinetuneJob,
        adapter: FinetuneAdapter,
        state: TrainingState,
        data: FinetuneData,
    ) -> object | None:
        """The best epoch's snapshot, `BASE` when none beat the base model on validation,
        or None when cancelled. The base model competes as epoch 0."""
        best_snapshot: object = BASE
        for epoch in range(1, job.request.settings.epochs + 1):
            if job.cancel_requested.is_set():
                job.state, job.message = "cancelled", f"Cancelled before epoch {epoch}"
                return None
            loss = adapter.train_epoch(state, data, epoch)
            metrics = adapter.evaluate(state, data.val) if data.val else {}
            job.history.append(EpochResult(epoch, loss, metrics))
            job.epoch = epoch
            score = metrics.get(adapter.primary_metric)
            if score is None or job.best_metric is None or score > job.best_metric:
                job.best_metric = score
                job.best_epoch = epoch
                best_snapshot = adapter.snapshot(state)
        return best_snapshot

    def _compare(self, job: FoundationFinetuneJob) -> None:
        before = job.baseline_metrics.get(job.primary_metric)
        after = job.final_metrics.get(job.primary_metric)
        if before is not None and after is not None and after < before:
            job.notes.append(
                f"On the held-out pictures the fine-tuned model scored {after:.3f} against the "
                f"baseline's {before:.3f}: it is saved, but it is not the better model here."
            )

    def _base_kept(self, job: FoundationFinetuneJob, base_val: float | None) -> None:
        """Nothing beat the base model: say so, and save nothing that would pretend."""
        tried = max((e.metrics.get(job.primary_metric, 0.0) for e in job.history), default=0.0)
        job.final_metrics = dict(job.baseline_metrics)
        job.notes.append(
            f"No epoch beat the base model on validation ({job.primary_metric} {base_val:.3f} "
            f"against at best {tried:.3f}), so nothing was saved: the base model is the better "
            "one for this data. More varied examples, or a lower learning rate, may change that."
            if base_val is not None
            else "No validation pictures to choose an epoch with; nothing was saved."
        )
        job.state, job.message = "complete", "The base model is kept"

    def _save(
        self,
        job: FoundationFinetuneJob,
        adapter: FinetuneAdapter,
        state: TrainingState,
        data: FinetuneData,
    ) -> None:
        request = job.request
        instance = FoundationInstanceStore(self._settings).save(
            existing_id=job.instance_id,
            name=request.name,
            base_model_id=get_requirements(request.finetune_id).model_id,
            dataset_ids=request.dataset_ids,
            class_names=data.class_names,
            metrics=job.final_metrics,
            epochs_trained=job.epoch,
            save=lambda directory: adapter.save(state, directory),
            finetune_id=request.finetune_id,
            recipe_id=request.recipe_id,
            baseline_metrics=job.baseline_metrics,
            weights_kind=adapter.weights_kind,
        )
        job.instance_id = instance.id


_runner: FoundationFinetuneRunner | None = None
_lock = threading.Lock()


def get_foundation_finetune_runner() -> FoundationFinetuneRunner:
    global _runner
    with _lock:
        if _runner is None:
            _runner = FoundationFinetuneRunner()
        return _runner


__all__ = [
    "EpochResult",
    "FinetuneRefusedError",
    "FinetuneRequest",
    "FoundationFinetuneJob",
    "FoundationFinetuneRunner",
    "get_foundation_finetune_runner",
]
