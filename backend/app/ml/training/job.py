"""Job state and the runner interface.

Separated from any concrete runner so that Wave 9's hyperscaler backend and today's
local one share one vocabulary, and callers can depend on the protocol alone.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Literal, Protocol

from torch import Tensor

from app.ml.training.config import TrainingConfig

JobState = Literal["pending", "running", "complete", "failed", "cancelled"]


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
    #: Set once the run is saved as a head instance, so the UI can link straight to it.
    head_instance_id: str | None = None
    cancel_requested: threading.Event = field(default_factory=threading.Event, repr=False)
    best_state: dict[str, Tensor] | None = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, entry: EpochRecord) -> None:
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


class JobRunner(Protocol):
    """What every runner provides. Wave 9's remote runner implements the same three."""

    def submit(self, config: TrainingConfig) -> TrainingJob: ...

    def get(self, job_id: str) -> TrainingJob | None: ...

    def cancel(self, job_id: str) -> bool: ...
