"""Fine-tuning a DINO backbone together with a task head (doc 95).

Doc 55's finding, applied where it holds: a head cannot carry a backbone (a modified
backbone inside a `HeadInstance` scored 0.000 in a fresh process), so unfreezing belongs
on a path that saves the **whole model**. This is that path. The last N blocks train with
a classification or segmentation head, and the result is saved as a *backbone variant*
with its own id, beside the head trained with it.

**The baseline is fair.** Before anything is unfrozen, the same head is trained for the
same epochs on the frozen backbone. That is what the user would get from the Training
tab's head path, and it is what the variant has to beat. An untrained head would make
any fine-tune look good.

It reuses the live pass (doc 55) rather than a second training loop: one definition of
how a picture becomes features, targets and a loss.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from app.core.config import Settings
from app.core.paths import resolve_model_dir
from app.finetune.adapter import FinetuneData, FinetuneSettings, TrainingState
from app.ml.backbone import Backbone, read_capabilities
from app.ml.foundation.variant import BACKBONE_DIR, HEAD_FILE
from app.ml.heads.builders import build_head
from app.ml.heads.decode import decode_for
from app.ml.heads.registry import HeadTypeSpec, get_head_type
from app.ml.preprocess import plan_preprocessing
from app.ml.training.live_loop import LivePass, evaluate_live, run_live_epoch
from app.ml.training.losses import loss_for
from app.ml.training.metrics import metrics_for
from app.ml.training.samples import TrainingSample
from app.ml.training.unfreeze import apply_unfreeze, optimiser_for

logger = logging.getLogger(__name__)

HEAD_FOR_TASK = {"classification": "linear-classifier", "segmentation": "linear-segmenter"}
DEFAULT_UNFROZEN = 4


@dataclass
class BackboneState:
    backbone: Backbone
    head: torch.nn.Module
    spec: HeadTypeSpec
    plan: Any
    optimiser: torch.optim.Optimizer
    num_classes: int
    settings: FinetuneSettings


def fresh_backbone(model_id: str, app_settings: Settings) -> Backbone:
    """A private copy: never the shared cache's, which every head in the app runs on."""
    from transformers import AutoImageProcessor, AutoModel

    directory = str(resolve_model_dir(model_id, app_settings))
    device = app_settings.resolved_device
    processor = AutoImageProcessor.from_pretrained(directory)  # type: ignore[no-untyped-call]
    model = AutoModel.from_pretrained(directory).to(device)
    return Backbone(read_capabilities(model_id), device, processor, model)


class BackboneAdapter:
    weights_kind = "backbone-variant"

    def __init__(self, finetune_id: str, backbone_id: str, task: str) -> None:
        self.finetune_id = finetune_id
        self.backbone_id = backbone_id
        spec = get_head_type(HEAD_FOR_TASK[task])
        assert spec is not None and spec.primary_metric is not None
        self.spec: HeadTypeSpec = spec
        self.primary_metric: str = spec.primary_metric

    def _live(self, state: BackboneState, samples: list[TrainingSample]) -> LivePass:
        return LivePass(state.backbone, state.plan, state.spec, samples, state.num_classes)

    def _num_classes(self, data: FinetuneData) -> int:
        # Segmentation puts background at index 0 (`classes_for_task`).
        extra = 1 if self.spec.task == "segmentation" else 0
        return len(data.class_names) + extra

    def _build(
        self, data: FinetuneData, settings: FinetuneSettings, app: Settings, blocks: int
    ) -> BackboneState:
        backbone = fresh_backbone(self.backbone_id, app)
        head = build_head(self.spec.id, backbone.capabilities, self._num_classes(data))
        head.to(backbone.device)
        apply_unfreeze(backbone, blocks)
        optimiser = optimiser_for(head, backbone, settings.learning_rate, 0.01)
        plan = plan_preprocessing(backbone.capabilities, self.spec)
        return BackboneState(
            backbone, head, self.spec, plan, optimiser, self._num_classes(data), settings
        )

    def prepare(
        self, data: FinetuneData, settings: FinetuneSettings, app_settings: Settings
    ) -> TrainingState:
        blocks = int(settings.options.get("unfreeze_blocks", DEFAULT_UNFROZEN))
        return self._build(data, settings, app_settings, blocks)

    def baseline(
        self, data: FinetuneData, settings: FinetuneSettings, app_settings: Settings
    ) -> dict[str, float]:
        """The same head, the same epochs, on the frozen backbone: the head path's result."""
        frozen = self._build(data, settings, app_settings, 0)
        for epoch in range(1, settings.epochs + 1):
            self.train_epoch(frozen, data, epoch)
        return self.evaluate(frozen, data.held_out)

    def train_epoch(self, state: TrainingState, data: FinetuneData, epoch: int) -> float:
        assert isinstance(state, BackboneState)
        live = self._live(state, data.train)
        indices = tuple(range(len(data.train)))
        return run_live_epoch(live, state.head, state.optimiser, loss_for(state.spec), indices)

    def evaluate(self, state: TrainingState, samples: list[TrainingSample]) -> dict[str, float]:
        assert isinstance(state, BackboneState)
        if not samples:
            return {}
        live = self._live(state, samples)
        _, outputs, targets = evaluate_live(
            live, state.head, loss_for(state.spec), tuple(range(len(samples)))
        )
        decode = decode_for(state.spec)
        decoded = [decode(out, state.plan.patch_size) for out in outputs]
        return metrics_for(state.spec)(decoded, targets) if decoded else {}

    def snapshot(self, state: TrainingState) -> object:
        assert isinstance(state, BackboneState)
        return (
            copy.deepcopy(state.backbone.model.state_dict()),
            copy.deepcopy(state.head.state_dict()),
        )

    def restore(self, state: TrainingState, snapshot: object) -> None:
        assert isinstance(state, BackboneState) and isinstance(snapshot, tuple)
        state.backbone.model.load_state_dict(snapshot[0])
        state.head.load_state_dict(snapshot[1])

    def save(self, state: TrainingState, directory: Path) -> None:
        assert isinstance(state, BackboneState)
        state.backbone.model.save_pretrained(str(directory / BACKBONE_DIR))
        state.backbone.processor.save_pretrained(str(directory / BACKBONE_DIR))
        torch.save({k: v.cpu() for k, v in state.head.state_dict().items()}, directory / HEAD_FILE)


__all__ = ["BackboneAdapter", "fresh_backbone"]
