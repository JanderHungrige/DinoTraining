"""What a model must provide to be fine-tuned by the shared runner (doc 93).

Doc 44's runner knew one model. Every model differs in four places only: how it turns a
sample into a training step, how it is scored, what is saved, and how it is loaded. An
adapter is those four places; the job lifecycle, the preflight, the split, the base
score, cancel and saving the best epoch are the runner's, once.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.ml.training.samples import TrainingSample


@dataclass
class FinetuneData:
    """Samples by side. `held_out` is what base and fine-tuned are compared on."""

    train: list[TrainingSample]
    val: list[TrainingSample]
    test: list[TrainingSample]
    class_names: tuple[str, ...]
    #: The datasets the samples came from — SAM 3 reads their phrases and checks (doc 108).
    dataset_ids: tuple[str, ...] = ()
    #: Set by the runner to the job's cancel flag, so a long epoch stops between pictures
    #: rather than only between epochs (found live on SAM 3, doc 96).
    stop: threading.Event | None = None

    @property
    def stopped(self) -> bool:
        return self.stop is not None and self.stop.is_set()

    @property
    def held_out(self) -> list[TrainingSample]:
        """The test side when it has pictures, else validation (and the job says so)."""
        return self.test or self.val


@dataclass
class FinetuneSettings:
    epochs: int = 10
    learning_rate: float = 1e-4
    seed: int = 42
    #: Adapter-specific options, e.g. DINOv3's unfrozen blocks (doc 95). The API fills
    #: every catalogue parameter here (doc 99); adapters read them with `param`.
    options: dict[str, float] = field(default_factory=dict)

    def as_parameters(self) -> dict[str, float | int | bool | str]:
        """Everything this run used, for the saved model's provenance (doc 99)."""
        return {
            **self.options,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "seed": self.seed,
        }


def param(settings: FinetuneSettings, family: str, key: str) -> float:
    """An adapter's option, or the catalogue's default for it (doc 99) — one source, so an
    adapter can never train with a value the ? popover does not show."""
    from app.params import family_for

    return float(family_for(family).value(settings.options, key))


def memory_budget(fraction: float, ceiling: int = 3 * 1024**3) -> int:
    """A share of this machine's physical memory, for caches of frozen features.

    A fixed 3 GB cache beside SAM 3's 3.4 GB of weights drove a 16 GB Mac into 24 GB of
    swap, and a training epoch that should take minutes did not finish in half an hour
    (doc 96). Budgets are a share of the machine instead.
    """
    try:
        total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        total = 8 * 1024**3
    return min(ceiling, int(total * fraction))


class TrainingState(Protocol):
    """Whatever an adapter keeps between calls: the model, its optimiser, caches."""


class FinetuneAdapter(Protocol):
    finetune_id: str
    #: The metric that picks the best epoch and compares base with fine-tuned.
    primary_metric: str
    #: What `save` writes: "full", "sam-mask-decoder" or "backbone-variant".
    weights_kind: str

    def prepare(
        self, data: FinetuneData, settings: FinetuneSettings, app_settings: Settings
    ) -> TrainingState:
        """Load the base model and set up training (frozen parts, optimiser)."""
        ...

    def train_epoch(self, state: TrainingState, data: FinetuneData, epoch: int) -> float:
        """One pass over `data.train`. Returns the mean loss."""
        ...

    def evaluate(self, state: TrainingState, samples: list[TrainingSample]) -> dict[str, float]:
        """Metrics of the model as it is now, on `samples`."""
        ...

    def snapshot(self, state: TrainingState) -> object:
        """A copy of the trained weights, to restore the best epoch later."""
        ...

    def restore(self, state: TrainingState, snapshot: object) -> None: ...

    def save(self, state: TrainingState, directory: Path) -> None:
        """Write what is needed to load the fine-tuned model again."""
        ...


__all__ = [
    "FinetuneAdapter",
    "FinetuneData",
    "FinetuneSettings",
    "TrainingState",
    "memory_budget",
    "param",
]
