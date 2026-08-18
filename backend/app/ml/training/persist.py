"""Turning a finished training job into a registered head instance.

Lives on the training side so `app.ml.heads` never imports `app.ml.training` — the
heads package is read by the API on every request and must stay free of the training
dependency graph.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from app.ml.backbone import BackboneCapabilities
from app.ml.heads.instances import TASK_LABELS, HeadInstance
from app.ml.heads.registry import HeadTypeSpec
from app.ml.heads.store import HeadInstanceStore
from app.ml.training.job import TrainingJob

logger = logging.getLogger(__name__)


class NothingToPersistError(ValueError):
    """The job produced no weights — there is no head to register."""


def default_name(spec: HeadTypeSpec, class_names: tuple[str, ...]) -> str:
    """A readable default so the user never faces a list of hex ids."""
    label = TASK_LABELS.get(spec.task, spec.task)
    if not class_names:
        return label
    if len(class_names) <= 2:
        return f"{label}: {', '.join(class_names)}"
    return f"{label}: {class_names[0]} +{len(class_names) - 1} more"


def register_trained_head(
    job: TrainingJob,
    spec: HeadTypeSpec,
    capabilities: BackboneCapabilities,
    store: HeadInstanceStore | None = None,
    name: str | None = None,
) -> HeadInstance:
    """Persist a completed job's best weights with full provenance.

    Refuses a job with no weights rather than writing an empty head: an instance that
    cannot be loaded is worse than no instance, because it only fails once the user
    selects it in a different tab.
    """
    if job.best_state is None:
        raise NothingToPersistError(
            f"Job {job.job_id} has no best weights — it {job.state} before completing an epoch"
        )

    store = store or HeadInstanceStore()
    final_metrics = job.history[job.best_epoch - 1].metrics if job.best_epoch else {}

    return store.register(
        name=name or default_name(spec, job.class_names),
        kind="trained-here",
        head_type_id=spec.id,
        task=spec.task,
        backbone_id=job.config.backbone_id,
        backbone_family=capabilities.family,
        embed_dim=capabilities.embed_dim,
        num_classes=len(job.class_names),
        weights=job.best_state,
        class_names=job.class_names,
        dataset_ids=job.config.dataset_ids,
        metrics=final_metrics,
        primary_metric=spec.primary_metric,
        primary_metric_value=job.best_metric,
        # The config snapshot is what makes a run reproducible; without it a checkpoint
        # records what it achieved but not how, and cannot be repeated or explained.
        config=asdict(job.config),
        epochs_trained=len(job.history),
        best_epoch=job.best_epoch,
    )
