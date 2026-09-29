"""Fine-tuning SAM 2's mask decoder on the user's own outlines (doc 94).

* **Only the mask decoder trains.** The image encoder is frozen, so each picture's
  embeddings are computed once and cached (fp16, on the CPU, within `CACHE_BUDGET_BYTES`;
  the rest are recomputed each epoch). The result is the decoder's weights alone: a few
  megabytes instead of the whole model.
* **Prompts come from the masks.** Each object is prompted with its own box, jittered
  during training so the decoder learns to cope with a loose box, exact at evaluation.
* **Loss** as SAM's own training: focal + dice on the mask logits, and the IoU head
  regressed onto the IoU it actually achieved.
* **Scored** as mIoU over held-out objects at the picture's own resolution, box-prompted.

Geometry follows the processor: pictures are stretched to 1024 px, boxes scaled with
them, and masks predicted at 256 px (doc 85's "stretch").
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from torch.nn import functional as F

from app.core.config import Settings
from app.core.paths import resolve_model_dir
from app.datasets.rle import rle_decode
from app.finetune.adapter import FinetuneData, FinetuneSettings, TrainingState
from app.ml.training.samples import TrainingSample

logger = logging.getLogger(__name__)

INPUT = 1024
LOW_RES = 256
CACHE_BUDGET_BYTES = 3 * 1024**3
#: Objects per picture per step, at most: a crowded picture is sampled, not all at once.
MAX_OBJECTS = 16
JITTER = 0.1
DECODER_FILE = "mask_decoder.pt"


@dataclass
class Sam2State:
    model: Any
    processor: Any
    device: str
    optimiser: torch.optim.Optimizer
    rng: random.Random
    cache: dict[str, list[torch.Tensor]] = field(default_factory=dict)
    cached_bytes: int = 0


def _objects(sample: TrainingSample) -> list[np.ndarray]:
    return [rle_decode(list(m.counts), m.size).astype(bool) for m in sample.masks]


def _box(mask: np.ndarray) -> tuple[float, float, float, float] | None:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1)


def _jittered(box: tuple[float, float, float, float], rng: random.Random) -> list[float]:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    return [
        x0 + rng.uniform(-JITTER, JITTER) * w,
        y0 + rng.uniform(-JITTER, JITTER) * h,
        x1 + rng.uniform(-JITTER, JITTER) * w,
        y1 + rng.uniform(-JITTER, JITTER) * h,
    ]


def _embeddings(
    state: Sam2State, sample: TrainingSample
) -> tuple[list[torch.Tensor], tuple[int, int]]:
    """The frozen encoder's output for a picture, cached while the budget lasts."""
    with Image.open(sample.path) as opened:
        image = opened.convert("RGB")
    size = (image.height, image.width)
    cached = state.cache.get(sample.path)
    if cached is not None:
        return [t.to(state.device, torch.float32) for t in cached], size
    pixels = state.processor(images=image, return_tensors="pt")["pixel_values"].to(state.device)
    with torch.no_grad():
        embeds = state.model.get_image_embeddings(pixels)
    stored = [t.detach().to("cpu", torch.float16) for t in embeds]
    nbytes = sum(t.element_size() * t.nelement() for t in stored)
    if state.cached_bytes + nbytes <= CACHE_BUDGET_BYTES:
        state.cache[sample.path] = stored
        state.cached_bytes += nbytes
    return embeds, size


def _scaled(boxes: list[list[float]], size: tuple[int, int]) -> torch.Tensor:
    h, w = size
    return torch.tensor(
        [[b[0] * INPUT / w, b[1] * INPUT / h, b[2] * INPUT / w, b[3] * INPUT / h] for b in boxes]
    )


def _low_res(masks: list[np.ndarray]) -> torch.Tensor:
    stacked = torch.from_numpy(np.stack(masks).astype(np.float32))[:, None]
    return F.interpolate(stacked, size=(LOW_RES, LOW_RES), mode="nearest")[:, 0]


def _loss(logits: torch.Tensor, iou_pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Focal + dice on the masks (SAM's 20:1), MSE of the IoU head against the IoU achieved."""
    prob = logits.sigmoid()
    bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    p_t = prob * target + (1 - prob) * (1 - target)
    focal_loss = (0.25 * (1 - p_t) ** 2 * bce).mean()
    inter = (prob * target).flatten(1).sum(1)
    dice = 1 - (2 * inter + 1) / (prob.flatten(1).sum(1) + target.flatten(1).sum(1) + 1)
    hard = (logits > 0).float()
    achieved = (hard * target).flatten(1).sum(1) / (
        (hard + target).clamp(max=1).flatten(1).sum(1) + 1e-6
    )
    return 20 * focal_loss + dice.mean() + F.mse_loss(iou_pred, achieved.detach())


class Sam2Adapter:
    primary_metric = "miou"
    weights_kind = "sam-mask-decoder"

    def __init__(self, finetune_id: str) -> None:
        self.finetune_id = finetune_id

    def prepare(
        self, data: FinetuneData, settings: FinetuneSettings, app_settings: Settings
    ) -> TrainingState:
        from transformers import Sam2Model, Sam2Processor

        directory = str(resolve_model_dir(self.finetune_id, app_settings))
        device = app_settings.resolved_device
        # A fresh instance, never the segmenter cache's: training the cached model would
        # change every other tab's SAM mid-session (doc 44's `fresh` rule).
        model = Sam2Model.from_pretrained(directory).to(device)  # type: ignore[arg-type]
        processor = Sam2Processor.from_pretrained(directory)
        for name, parameter in model.named_parameters():
            parameter.requires_grad = name.startswith("mask_decoder.")
        trainable = [p for p in model.parameters() if p.requires_grad]
        optimiser = torch.optim.AdamW(trainable, lr=settings.learning_rate, weight_decay=1e-4)
        model.eval()
        return Sam2State(model, processor, device, optimiser, random.Random(settings.seed))

    def _step(self, state: Sam2State, sample: TrainingSample) -> float | None:
        masks = _objects(sample)
        pairs = [(m, b) for m in masks if (b := _box(m)) is not None]
        if not pairs:
            return None
        state.rng.shuffle(pairs)
        pairs = pairs[:MAX_OBJECTS]
        embeds, size = _embeddings(state, sample)
        boxes = _scaled([_jittered(b, state.rng) for _, b in pairs], size).to(state.device)
        out = state.model(image_embeddings=embeds, input_boxes=boxes[None], multimask_output=False)
        logits = out.pred_masks[0, :, 0]
        target = _low_res([m for m, _ in pairs]).to(state.device)
        loss = _loss(logits, out.iou_scores[0, :, 0], target)
        state.optimiser.zero_grad(set_to_none=True)
        loss.backward()  # type: ignore[no-untyped-call]
        state.optimiser.step()
        return float(loss.detach())

    def train_epoch(self, state: TrainingState, data: FinetuneData, epoch: int) -> float:
        assert isinstance(state, Sam2State)
        state.model.mask_decoder.train()
        order = data.train[:]
        state.rng.shuffle(order)
        losses = [loss for sample in order if (loss := self._step(state, sample)) is not None]
        state.model.mask_decoder.eval()
        return sum(losses) / max(1, len(losses))

    def evaluate(self, state: TrainingState, samples: list[TrainingSample]) -> dict[str, float]:
        """Mean IoU over every held-out object, at the picture's own size."""
        assert isinstance(state, Sam2State)
        ious: list[float] = []
        for sample in samples:
            pairs = [(m, b) for m in _objects(sample) if (b := _box(m)) is not None]
            if not pairs:
                continue
            embeds, size = _embeddings(state, sample)
            boxes = _scaled([list(b) for _, b in pairs], size).to(state.device)
            with torch.no_grad():
                out = state.model(
                    image_embeddings=embeds, input_boxes=boxes[None], multimask_output=False
                )
            full = F.interpolate(
                out.pred_masks[0].float(), size=size, mode="bilinear", align_corners=False
            )
            predicted = (full[:, 0] > 0).cpu().numpy()
            for (truth, _), guess in zip(pairs, predicted, strict=True):
                union = np.logical_or(truth, guess).sum()
                ious.append(float(np.logical_and(truth, guess).sum() / union) if union else 1.0)
        return {"miou": float(np.mean(ious))} if ious else {}

    def snapshot(self, state: TrainingState) -> object:
        assert isinstance(state, Sam2State)
        return {k: v.detach().clone() for k, v in state.model.mask_decoder.state_dict().items()}

    def restore(self, state: TrainingState, snapshot: object) -> None:
        assert isinstance(state, Sam2State) and isinstance(snapshot, dict)
        state.model.mask_decoder.load_state_dict(snapshot)

    def save(self, state: TrainingState, directory: Path) -> None:
        assert isinstance(state, Sam2State)
        cpu = {k: v.detach().cpu() for k, v in state.model.mask_decoder.state_dict().items()}
        torch.save(cpu, directory / DECODER_FILE)


__all__ = ["DECODER_FILE", "Sam2Adapter"]
