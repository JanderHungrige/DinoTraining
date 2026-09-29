"""What a model must provide to be fine-tuned by the shared runner (doc 93).

Doc 44's runner knew one model. Every model differs in four places only: how it turns a
sample into a training step, how it is scored, what is saved, and how it is loaded. An
adapter is those four places; the job lifecycle, the preflight, the split, the base
score, cancel and saving the best epoch are the runner's, once.
"""

from __future__ import annotations

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

    @property
    def held_out(self) -> list[TrainingSample]:
        """The test side when it has pictures, else validation (and the job says so)."""
        return self.test or self.val


@dataclass
class FinetuneSettings:
    epochs: int = 10
    learning_rate: float = 1e-4
    seed: int = 42
    #: Adapter-specific options, e.g. DINOv3's unfrozen blocks (doc 95).
    options: dict[str, float] = field(default_factory=dict)


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


__all__ = ["FinetuneAdapter", "FinetuneData", "FinetuneSettings", "TrainingState"]
