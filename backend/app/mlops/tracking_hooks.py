"""Where MLflow tracking meets the two runners (doc 123).

Head training: a job hook attaches listeners to each new `TrainingJob` (epoch, finish,
saved), so the runner does not know about tracking. Fine-tuning: `finetune_tracker` gives
the runner one object to call at each step.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.ml.training.job import JOB_HOOKS, TrainingJob
from app.mlops.tracking import MlflowTracker, NullTracker, start_run


def _head_tags(job: TrainingJob) -> dict[str, str]:
    config = job.config
    return {
        "dinotraining.kind": "head",
        "dinotraining.base": config.backbone_id,
        "dinotraining.head_type": config.head_type_id,
        "dinotraining.datasets": ",".join(config.dataset_ids),
        "dinotraining.recipe": str(getattr(config, "recipe_id", None) or ""),
    }


def _attach(job: TrainingJob) -> None:
    config = job.config
    name = (
        str(getattr(config, "name", "") or "") or f"{config.head_type_id} on {config.backbone_id}"
    )
    tracker = start_run(name, asdict(config), _head_tags(job), job.notes.append)
    if isinstance(tracker, NullTracker):
        return

    def listen(event: str, j: TrainingJob) -> None:
        if event == "epoch":
            last = j.history[-1]
            tracker.epoch(
                last.epoch,
                {"train_loss": last.train_loss, "val_loss": last.val_loss, **last.metrics},
            )
        elif event == "saved" and j.head_instance_id:
            tracker.saved("heads", j.head_instance_id)
        elif event == "finish" and (j.state != "complete" or j.best_state is None):
            # Complete with weights ends on "saved", after the card and bundle are uploaded.
            tracker.finished(j.state)

    job.listeners.append(listen)


def install() -> None:
    """Register the head-training hook once, at startup."""
    if _attach not in JOB_HOOKS:
        JOB_HOOKS.append(_attach)


def finetune_tracker(job: Any) -> NullTracker | MlflowTracker:
    request = job.request
    tags = {
        "dinotraining.kind": "finetuned",
        "dinotraining.base": request.finetune_id,
        "dinotraining.datasets": ",".join(request.dataset_ids),
        "dinotraining.recipe": request.recipe_id or "",
    }
    return start_run(request.name, request.settings.as_parameters(), tags, job.notes.append)


__all__ = ["finetune_tracker", "install"]
