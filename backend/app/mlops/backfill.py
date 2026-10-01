"""Send the models trained before MLflow was set up (doc 124) — each once.

One run per trained head and fine-tuned model: its settings, final metrics (every epoch
when the history was recorded), card, bundle and a registry version. A model already in
the experiment (tagged `dinotraining.model = <kind>:<id>`) is skipped.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.ml.foundation.instances import FoundationInstanceStore
from app.ml.heads.store import HeadInstanceStore
from app.mlops.mlflow_client import MlflowClient, MlflowError
from app.mlops.tracking import flatten, log_model

logger = logging.getLogger(__name__)


@dataclass
class BackfillJob:
    job_id: str
    state: str = "running"  # running | complete | failed
    total: int = 0
    sent: int = 0
    skipped: int = 0
    failed: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Model:
    kind: str
    instance_id: str
    name: str
    created_at: str
    params: dict[str, Any]
    tags: dict[str, str]
    metrics: dict[str, float]
    epochs: int
    history: tuple[dict[str, object], ...] | None


_jobs: dict[str, BackfillJob] = {}
_lock = threading.Lock()


def _models() -> tuple[list[_Model], int]:
    """(models trained here, count of heads not trained here)."""
    found: list[_Model] = []
    heads = HeadInstanceStore().list_all()
    for head in heads:
        if head.kind != "trained-here":
            continue
        found.append(
            _Model(
                "heads", head.id, head.name, head.created_at, dict(head.config),
                {"dinotraining.kind": "head", "dinotraining.base": head.backbone_id,
                 "dinotraining.datasets": ",".join(head.dataset_ids)},
                head.metrics, head.epochs_trained, head.history,
            )
        )  # fmt: skip
    for tuned in FoundationInstanceStore().list_all():
        metrics = {
            **tuned.metrics,
            **{f"baseline_{k}": v for k, v in tuned.baseline_metrics.items()},
        }
        found.append(
            _Model(
                "finetuned", tuned.id, tuned.name, tuned.created_at, dict(tuned.parameters),
                {"dinotraining.kind": "finetuned", "dinotraining.base": tuned.base_model_id,
                 "dinotraining.datasets": ",".join(tuned.dataset_ids),
                 "dinotraining.recipe": tuned.recipe_id or ""},
                metrics, tuned.epochs_trained, tuned.history,
            )
        )  # fmt: skip
    return found, sum(1 for head in heads if head.kind != "trained-here")


def _start_ms(created_at: str) -> int | None:
    try:
        return int(datetime.fromisoformat(created_at).timestamp() * 1000)
    except ValueError:
        return None


def _send(client: MlflowClient, experiment: str, model: _Model) -> None:
    tags = {**model.tags, "dinotraining.backfilled": "true"}
    run_id, artifacts = client.create_run(experiment, model.name, tags, _start_ms(model.created_at))
    client.log_params(run_id, flatten(model.params))
    if model.history:
        for entry in model.history:
            step = int(str(entry.get("epoch", 0)))
            values = {
                k: float(v)
                for k, v in entry.items()
                if k in ("train_loss", "val_loss") and isinstance(v, int | float)
            }
            metrics = entry.get("metrics")
            if isinstance(metrics, dict):
                values.update({str(k): float(v) for k, v in metrics.items()})
            client.log_metrics(run_id, values, step)
    client.log_metrics(run_id, model.metrics, model.epochs)
    log_model(client, get_settings(), run_id, artifacts, model.kind, model.instance_id)
    client.end_run(run_id, "FINISHED")


def _run(job: BackfillJob) -> None:
    settings = get_settings()
    try:
        client = MlflowClient(settings)
        experiment = client.experiment_id(settings.mlflow_experiment)
        models, not_trained = _models()
        job.total, job.skipped = len(models) + not_trained, not_trained
        if not_trained:
            job.notes.append(f"{not_trained} heads were not trained here (defaults, imports).")
        for model in models:
            key = f"{model.kind}:{model.instance_id}"
            if client.search_runs(experiment, "dinotraining.model", key):
                job.skipped += 1
                continue
            try:
                _send(client, experiment, model)
                job.sent += 1
            except (MlflowError, OSError, LookupError, ValueError) as error:
                if isinstance(error, MlflowError) and "not reachable" in str(error):
                    raise
                logger.warning("Backfill of %s failed: %s", key, error)
                job.failed += 1
                job.notes.append(f"{model.name}: {error}")
        job.state = "complete"
    except MlflowError as error:
        logger.warning("MLflow backfill stopped: %s", error)
        job.notes.append(f"MLflow: {error}")
        job.state = "failed"


def start_backfill() -> BackfillJob:
    job = BackfillJob(job_id=uuid.uuid4().hex)
    with _lock:
        _jobs[job.job_id] = job
    threading.Thread(target=_run, args=(job,), name="mlflow-backfill", daemon=True).start()
    return job


def get_backfill(job_id: str) -> BackfillJob | None:
    with _lock:
        return _jobs.get(job_id)


def as_dict(job: BackfillJob) -> dict[str, Any]:
    return asdict(job)


__all__ = ["BackfillJob", "as_dict", "get_backfill", "start_backfill"]
