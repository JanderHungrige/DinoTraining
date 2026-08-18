"""Local execution backend for training jobs.

Callers depend on :class:`app.ml.training.job.JobRunner`, never on this class. Wave 6
adds a hyperscaler runner by implementing the same three methods and swapping the
construction in :func:`get_job_runner` — no call site changes.
"""

from __future__ import annotations

import logging
import threading
import uuid

import torch

from app.datasets.store import DatasetStore
from app.ml.backbone import load_backbone, read_capabilities
from app.ml.heads.builders import build_head
from app.ml.heads.registry import HeadTypeSpec, get_head_type
from app.ml.preprocess import plan_preprocessing
from app.ml.training.config import TrainingConfig, split_indices
from app.ml.training.decode import decode_for
from app.ml.training.job import EpochRecord, TrainingJob
from app.ml.training.loop import evaluate, is_better, precompute_cache, run_epoch
from app.ml.training.losses import loss_for
from app.ml.training.metrics import metrics_for
from app.ml.training.samples import build_samples, samples_for_task

logger = logging.getLogger(__name__)


class LocalJobRunner:
    """Trains on this machine, in a worker thread.

    Threads rather than processes, for the same reason Wave 1's downloads use them: the
    work releases the GIL inside torch, and a thread keeps the loaded backbone resident
    instead of re-paying a multi-second load per job.
    """

    def __init__(self, store: DatasetStore | None = None) -> None:
        self._jobs: dict[str, TrainingJob] = {}
        self._lock = threading.Lock()
        self._store = store or DatasetStore()

    # --- JobRunner protocol -----------------------------------------------------

    def submit(self, config: TrainingConfig) -> TrainingJob:
        spec = get_head_type(config.head_type_id)
        if spec is None:
            raise LookupError(f"Unknown head type: {config.head_type_id}")
        if not spec.trainable:
            # The check that makes the registry's usable/trainable split real rather
            # than decorative.
            raise ValueError(
                f"{spec.title} cannot be trained in this app — use its pretrained "
                "default head for inference instead."
            )

        job = TrainingJob(job_id=uuid.uuid4().hex, config=config, total_epochs=config.epochs)
        with self._lock:
            self._jobs[job.job_id] = job

        threading.Thread(
            target=self._run, args=(job, spec), name=f"train-{job.job_id[:8]}", daemon=True
        ).start()
        return job

    def get(self, job_id: str) -> TrainingJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None or job.finished:
            return False
        job.cancel_requested.set()
        return True

    # --- execution --------------------------------------------------------------

    def _run(self, job: TrainingJob, spec: HeadTypeSpec) -> None:
        try:
            job.state = "running"
            self._train(job, spec)
        except Exception as exc:  # noqa: BLE001 - surfaced on the job, logged with context
            logger.exception("Training job %s failed", job.job_id)
            job.finish("failed", str(exc))

    def _train(self, job: TrainingJob, spec: HeadTypeSpec) -> None:
        config = job.config
        capabilities = read_capabilities(config.backbone_id)
        backbone = load_backbone(config.backbone_id)
        plan = plan_preprocessing(capabilities, spec)

        sample_set = build_samples(self._store, config.dataset_ids)
        job.class_names = sample_set.class_names
        job.skipped_mixed_class_images = sample_set.mixed_class_images

        if sample_set.num_classes == 0:
            raise ValueError("No positive boxes found in the selected datasets — nothing to learn")
        usable = samples_for_task(sample_set, spec.task)
        if not usable:
            raise ValueError("No usable training samples for this head type")

        head = build_head(config.head_type_id, capabilities, sample_set.num_classes)
        head.to(backbone.device)
        optimiser = torch.optim.AdamW(
            head.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
        )
        compute_loss = loss_for(spec)
        compute_metrics = metrics_for(spec)
        decode = decode_for(spec)

        cache = precompute_cache(backbone, plan, spec, usable, sample_set.num_classes)
        if not cache:
            raise ValueError("None of the selected images could be read")

        split = split_indices(
            len(cache), config.val_fraction, config.test_fraction, config.split_seed
        )
        assert spec.primary_metric is not None  # 08 guarantees this for trainable heads
        mode = spec.primary_metric_mode or "max"
        patience = 0

        for epoch in range(1, config.epochs + 1):
            if job.cancel_requested.is_set():
                job.finish("cancelled", f"Cancelled at epoch {epoch}")
                return

            train_loss = run_epoch(head, optimiser, compute_loss, cache, split.train)
            val_loss, outputs, targets = evaluate(head, compute_loss, cache, split.val)
            # Decode before metrics: detection metrics need boxes, not per-cell logits.
            decoded = [decode(out, plan.patch_size) for out in outputs]
            metrics = compute_metrics(decoded, targets) if decoded else {}
            job.record(
                EpochRecord(epoch=epoch, train_loss=train_loss, val_loss=val_loss, metrics=metrics)
            )

            current = metrics.get(spec.primary_metric)
            if current is None:
                # No validation split, so there is nothing to select or stop on. Keep
                # the latest weights rather than none at all.
                job.best_state = {k: v.detach().clone() for k, v in head.state_dict().items()}
                job.best_epoch = epoch
                continue

            if is_better(current, job.best_metric, mode):
                job.best_metric = current
                job.best_epoch = epoch
                job.best_state = {k: v.detach().clone() for k, v in head.state_dict().items()}
                patience = 0
            else:
                patience += 1
                if patience >= config.early_stopping_patience:
                    job.finish("complete", f"Early stop at epoch {epoch}")
                    return

        job.finish("complete", f"Finished {config.epochs} epochs")


_runner: LocalJobRunner | None = None
_runner_lock = threading.Lock()


def get_job_runner() -> LocalJobRunner:
    """Process-wide runner. Wave 6 swaps the construction here, not at call sites."""
    global _runner
    with _runner_lock:
        if _runner is None:
            _runner = LocalJobRunner()
        return _runner
