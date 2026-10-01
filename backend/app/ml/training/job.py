"""Job state and the runner interface.

Separated from any concrete runner so that Wave 16's hyperscaler backend and today's
local one share one vocabulary, and callers can depend on the protocol alone.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from torch import Tensor

from app.ml.training.config import TrainingConfig

JobState = Literal["pending", "running", "complete", "failed", "cancelled"]

logger = logging.getLogger(__name__)

#: Doc 123: called with each new job; MLflow tracking registers here at startup. A hook
#: attaches listeners — ("epoch" | "finish" | "saved", job) — without the runner knowing.
JOB_HOOKS: list[Callable[[TrainingJob], None]] = []


@dataclass(frozen=True, slots=True)
class EpochRecord:
    """One epoch's results.

    ``metrics`` keys come from the head spec's declared metric names — the stream in
    `13` reads whatever keys are present rather than hardcoding a task's metrics.
    """

    epoch: int
    train_loss: float
    val_loss: float
    metrics: dict[str, float]


@dataclass
class TrainingJob:
    """Live state of one run. Mirrors Wave 1's DownloadJob shape deliberately."""

    job_id: str
    config: TrainingConfig
    state: JobState = "pending"
    epoch: int = 0
    total_epochs: int = 0
    history: list[EpochRecord] = field(default_factory=list)
    best_metric: float | None = None
    best_epoch: int | None = None
    class_names: tuple[str, ...] = ()
    skipped_mixed_class_images: int = 0
    #: Backbone parameter split when blocks are unfrozen (doc 55). **Reported, not
    #: just logged**, for doc 44's reason: "did it actually unfreeze?" is the question
    #: the feature rests on, and a silent no-op looks exactly like a slow success.
    frozen_parameters: int = 0
    trainable_parameters: int = 0
    message: str = ""
    #: What preparation did on this run that the user should know (doc 87): flips turned
    #: off for a class, fewer augmented copies than asked for.
    notes: list[str] = field(default_factory=list)
    #: The best weights scored once on the test side (doc 90). Empty without a test side.
    test_metrics: dict[str, float] = field(default_factory=dict)
    #: Set once the run is saved as a head instance, so the UI can link straight to it.
    head_instance_id: str | None = None
    cancel_requested: threading.Event = field(default_factory=threading.Event, repr=False)
    best_state: dict[str, Tensor] | None = field(default=None, repr=False)
    listeners: list[Callable[[str, TrainingJob], None]] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        for hook in JOB_HOOKS:
            hook(self)

    def _tell(self, event: str) -> None:
        for listener in self.listeners:
            try:
                listener(event, self)
            except Exception:  # noqa: BLE001 - a listener must never break training
                logger.exception("Job %s listener failed on %s", self.job_id, event)

    def record(self, entry: EpochRecord) -> None:
        with self._lock:
            self.history.append(entry)
            self.epoch = entry.epoch
        self._tell("epoch")

    def finish(self, state: JobState, message: str = "") -> None:
        with self._lock:
            self.state = state
            self.message = message
        self._tell("finish")

    def mark_saved(self, instance_id: str) -> None:
        """The run is saved as a head instance (so the UI can link straight to it)."""
        self.head_instance_id = instance_id
        self._tell("saved")

    @property
    def finished(self) -> bool:
        return self.state in {"complete", "failed", "cancelled"}


class JobRunner(Protocol):
    """What every runner provides. Wave 16's remote runner implements the same three."""

    def submit(self, config: TrainingConfig) -> TrainingJob: ...

    def get(self, job_id: str) -> TrainingJob | None: ...

    def cancel(self, job_id: str) -> bool: ...
