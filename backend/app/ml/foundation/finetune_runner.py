"""Running and tracking a fine-tune (doc 44).

Mirrors `training/runner.py`'s *shape* — submit, poll, cancel, a job carrying live
history — so the UI can watch it with the machinery Wave 2 already built. It does not
reuse that runner, because the two loops genuinely differ: there is no feature cache and
no `HeadTypeSpec`, and forcing one loop to serve both would put a branch in the module
whose whole job is not to have one.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import torch
from PIL import Image

from app.core.config import Settings, get_settings
from app.datasets.store import DatasetStore
from app.ml.foundation.finetune import (
    FinetuneConfig,
    FinetuneEpoch,
    evaluate,
    freeze_backbone,
    load_samples,
    prepared_model,
    to_detr_labels,
)
from app.ml.foundation.instances import FoundationInstanceStore
from app.ml.training.job import JobState
from app.ml.training.samples import TrainingSample

logger = logging.getLogger(__name__)


@dataclass
class FinetuneJob:
    """Live state of one fine-tune. Mutated by the worker, read by the API."""

    job_id: str
    config: FinetuneConfig
    state: JobState = "pending"
    epoch: int = 0
    total_epochs: int = 0
    history: list[FinetuneEpoch] = field(default_factory=list)
    best_metric: float | None = None
    class_names: tuple[str, ...] = ()
    frozen_parameters: int = 0
    trainable_parameters: int = 0
    message: str = ""
    instance_id: str | None = None
    cancel_requested: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, entry: FinetuneEpoch) -> None:
        with self._lock:
            self.history.append(entry)
            self.epoch = entry.epoch

    def finish(self, state: JobState, message: str = "") -> None:
        with self._lock:
            self.state = state
            self.message = message

    @property
    def finished(self) -> bool:
        return self.state in {"complete", "failed", "cancelled"}


class FinetuneRunner:
    """One fine-tune at a time, on a worker thread."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._jobs: dict[str, FinetuneJob] = {}
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="finetune")

    def list_all(self) -> list[FinetuneJob]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> FinetuneJob | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.finished:
            return False
        job.cancel_requested.set()
        return True

    def submit(self, config: FinetuneConfig) -> FinetuneJob:
        job = FinetuneJob(
            job_id=uuid.uuid4().hex, config=config, total_epochs=config.epochs
        )
        self._jobs[job.job_id] = job
        self._pool.submit(self._run, job)
        return job

    def _run(self, job: FinetuneJob) -> None:
        try:
            job.state = "running"
            self._train(job)
        except Exception as exc:  # noqa: BLE001 - surfaced on the job, logged with context
            logger.exception("Fine-tune job %s failed", job.job_id)
            job.finish("failed", str(exc))

    def _train(self, job: FinetuneJob) -> None:
        config = job.config
        train, validation, class_names = load_samples(DatasetStore(self._settings), config)
        job.class_names = class_names

        model = prepared_model(
            config.foundation_id, len(class_names), class_names, self._settings
        )
        module = model.model
        job.frozen_parameters, job.trainable_parameters = freeze_backbone(
            module, config.unfreeze_blocks
        )
        logger.info(
            "Fine-tuning %s: %d frozen, %d trainable parameters",
            config.foundation_id,
            job.frozen_parameters,
            job.trainable_parameters,
        )

        # Two groups when the backbone is open: the decoder is being adapted and the
        # backbone nudged. One shared rate is the setting that makes unfreezing look like a
        # bad idea — at the decoder's rate a pretrained ViT is destroyed in one epoch.
        backbone_params = [
            p
            for p in module.get_submodule("model.backbone").parameters()
            if bool(p.requires_grad)
        ]
        backbone_ids = {id(p) for p in backbone_params}
        rest = [
            p for p in module.parameters() if bool(p.requires_grad) and id(p) not in backbone_ids
        ]
        groups: list[dict[str, object]] = [{"params": rest, "lr": config.learning_rate}]
        if backbone_params:
            groups.append(
                {
                    "params": backbone_params,
                    "lr": config.learning_rate * config.backbone_lr_scale,
                }
            )
        optimiser = torch.optim.AdamW(
            groups, lr=config.learning_rate, weight_decay=config.weight_decay
        )

        best = -1.0
        for epoch in range(1, config.epochs + 1):
            if job.cancel_requested.is_set():
                job.finish("cancelled", f"Cancelled before epoch {epoch}")
                return

            loss = self._one_epoch(model, module, optimiser, train)
            metrics = evaluate(model, validation) if validation else {}
            job.record(FinetuneEpoch(epoch=epoch, train_loss=loss, metrics=metrics))

            score = metrics.get("map", 0.0)
            if score > best:
                best = score
                job.best_metric = score
                self._save(job, model, class_names)

        job.finish("complete", f"Best map {best:.4f}")

    def _one_epoch(
        self,
        model: object,
        module: torch.nn.Module,
        optimiser: torch.optim.Optimizer,
        samples: list[TrainingSample],
    ) -> float:
        module.train()
        processor = model.processor  # type: ignore[attr-defined]
        device = model.device  # type: ignore[attr-defined]
        total = 0.0

        for sample in samples:
            with Image.open(sample.path) as opened:
                image = opened.convert("RGB")
            inputs = processor(images=image, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            labels = [to_detr_labels(sample, device)]

            outputs = module(**inputs, labels=labels)
            loss = outputs.loss
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            # DETR losses spike on the first steps of a re-opened classifier; clipping is
            # what stops one bad batch undoing a COCO-pretrained decoder.
            torch.nn.utils.clip_grad_norm_(
                [p for p in module.parameters() if p.requires_grad], max_norm=0.1
            )
            optimiser.step()
            total += float(loss.detach())

        module.eval()
        return total / max(len(samples), 1)

    def _save(self, job: FinetuneJob, model: object, class_names: tuple[str, ...]) -> None:
        """Persist the best epoch so far. Saved *during* the run, not after, so a cancelled
        or crashed job still leaves the best model it reached."""
        store = FoundationInstanceStore(self._settings)
        instance = store.save(
            existing_id=job.instance_id,
            name=job.config.name,
            base_model_id=job.config.foundation_id,
            dataset_ids=job.config.dataset_ids,
            class_names=class_names,
            metrics=job.history[-1].metrics if job.history else {},
            epochs_trained=job.epoch,
            save=lambda directory: _write(model, Path(directory)),
        )
        job.instance_id = instance.id


def _write(model: object, directory: Path) -> None:
    """The store has already created `directory`."""
    model.model.save_pretrained(str(directory))  # type: ignore[attr-defined]
    model.processor.save_pretrained(str(directory))  # type: ignore[attr-defined]


_runner: FinetuneRunner | None = None


def get_finetune_runner() -> FinetuneRunner:
    """Process-wide runner. Wave 9 swaps the construction here, not at call sites."""
    global _runner
    if _runner is None:
        _runner = FinetuneRunner()
    return _runner


__all__ = ["FinetuneJob", "FinetuneRunner", "get_finetune_runner"]
