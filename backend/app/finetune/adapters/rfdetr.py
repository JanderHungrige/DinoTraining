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

from app.core.config import Settings
from app.finetune.adapter import FinetuneData, FinetuneSettings, TrainingState
from app.ml.foundation.detect import RfDetrModel
from app.ml.foundation.finetune import evaluate, freeze_backbone, prepared_model, to_detr_labels
from app.ml.training.samples import TrainingSample

#: Gradient clip, doc 44's: DETR losses spike on a re-opened classifier's first steps.
MAX_NORM = 0.1


@dataclass
class RfDetrState:
    model: RfDetrModel
    optimiser: torch.optim.Optimizer


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
        freeze_backbone(model.model, int(settings.options.get("unfreeze_blocks", 0)))
        trainable = [p for p in model.model.parameters() if p.requires_grad]
        optimiser = torch.optim.AdamW(trainable, lr=settings.learning_rate, weight_decay=1e-4)
        return RfDetrState(model, optimiser)

    def train_epoch(self, state: TrainingState, data: FinetuneData, epoch: int) -> float:
        assert isinstance(state, RfDetrState)
        module, processor = state.model.model, state.model.processor
        module.train()
        total = 0.0
        for sample in data.train:
            with Image.open(sample.path) as opened:
                image = opened.convert("RGB")
            inputs = processor(images=image, return_tensors="pt")  # type: ignore[operator]
            inputs = {k: v.to(state.model.device) for k, v in inputs.items()}
            loss = module(**inputs, labels=[to_detr_labels(sample, state.model.device)]).loss
            state.optimiser.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                [p for p in module.parameters() if p.requires_grad], max_norm=MAX_NORM
            )
            state.optimiser.step()
            total += float(loss.detach())
        module.eval()
        return total / max(1, len(data.train))

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
