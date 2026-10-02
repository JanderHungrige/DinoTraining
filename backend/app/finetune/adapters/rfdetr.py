"""RF-DETR through the shared runner (docs 44, 93): doc 44's pieces, behind the adapter.

The base model's score here is near zero by construction: its classifier is re-opened for
the user's classes, so before training it knows none of them. That is the honest baseline
for a detector learning new classes; SAM (doc 94), which is class-agnostic, is where the
base-vs-fine-tuned comparison says more.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image

from app.cloud.pictures import ensure_local
from app.core.config import Settings
from app.finetune.adapter import FinetuneData, FinetuneSettings, TrainingState, param
from app.ml.foundation.detect import RfDetrModel
from app.ml.foundation.finetune import evaluate, freeze_backbone, prepared_model, to_detr_labels
from app.ml.training.samples import TrainingSample

FAMILY = "rf-detr"


@dataclass
class RfDetrState:
    model: RfDetrModel
    optimiser: torch.optim.Optimizer
    #: Doc 44's clip: DETR losses spike on a re-opened classifier's first steps.
    max_norm: float = 0.1
    #: Pictures per correction, by gradient accumulation (doc 99).
    per_step: int = 1


class RfDetrAdapter:
    primary_metric = "map"
    weights_kind = "full"

    def __init__(self, finetune_id: str) -> None:
        self.finetune_id = finetune_id

    def prepare(
        self, data: FinetuneData, settings: FinetuneSettings, app_settings: Settings
    ) -> TrainingState:
        model = prepared_model(
            self.finetune_id, len(data.class_names), data.class_names, app_settings
        )
        freeze_backbone(model.model, int(param(settings, FAMILY, "unfreeze_blocks")))
        trainable = [p for p in model.model.parameters() if p.requires_grad]
        optimiser = torch.optim.AdamW(
            trainable,
            lr=settings.learning_rate,
            weight_decay=param(settings, FAMILY, "weight_decay"),
        )
        return RfDetrState(
            model,
            optimiser,
            max_norm=param(settings, FAMILY, "max_grad_norm"),
            per_step=int(param(settings, FAMILY, "batch_size")),
        )

    def train_epoch(self, state: TrainingState, data: FinetuneData, epoch: int) -> float:
        assert isinstance(state, RfDetrState)
        module, processor = state.model.model, state.model.processor
        module.train()
        total, pending = 0.0, 0
        state.optimiser.zero_grad(set_to_none=True)
        for sample in data.train:
            if data.stopped:
                break
            with Image.open(ensure_local(sample.path)) as opened:
                image = opened.convert("RGB")
            inputs = processor(images=image, return_tensors="pt")  # type: ignore[operator]
            inputs = {k: v.to(state.model.device) for k, v in inputs.items()}
            loss = module(**inputs, labels=[to_detr_labels(sample, state.model.device)]).loss
            (loss / state.per_step).backward()
            pending += 1
            if pending == state.per_step:
                self._step(state)
                pending = 0
            total += float(loss.detach())
        if pending:
            self._step(state)
        module.eval()
        return total / max(1, len(data.train))

    @staticmethod
    def _step(state: RfDetrState) -> None:
        trainable = [p for p in state.model.model.parameters() if p.requires_grad]
        torch.nn.utils.clip_grad_norm_(trainable, max_norm=state.max_norm)
        state.optimiser.step()
        state.optimiser.zero_grad(set_to_none=True)

    def evaluate(self, state: TrainingState, samples: list[TrainingSample]) -> dict[str, float]:
        assert isinstance(state, RfDetrState)
        return evaluate(state.model, samples) if samples else {}

    def snapshot(self, state: TrainingState) -> object:
        assert isinstance(state, RfDetrState)
        return {k: v.detach().clone() for k, v in state.model.model.state_dict().items()}

    def restore(self, state: TrainingState, snapshot: object) -> None:
        assert isinstance(state, RfDetrState) and isinstance(snapshot, dict)
        state.model.model.load_state_dict(snapshot)

    def save(self, state: TrainingState, directory: Path) -> None:
        assert isinstance(state, RfDetrState)
        state.model.model.save_pretrained(str(directory))  # type: ignore[operator]
        state.model.processor.save_pretrained(str(directory))  # type: ignore[attr-defined]


__all__ = ["RfDetrAdapter"]
