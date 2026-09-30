"""Fine-tuning SAM 3 on the user's phrases and outlines (doc 96).

SAM 3 is prompted by a noun phrase and returns every instance of it: a DETR-style set of
200 queries, each with a mask, a box and a score, plus a presence score for the phrase.
Training it therefore needs what DETR needs, which `transformers` does not ship: a
Hungarian match between queries and ground-truth objects, then losses on the match.

* **Frozen:** the image and text encoders (825 M of 840 M parameters). Image features are
  cached per picture (fp16, CPU, within `CACHE_BUDGET_BYTES`); position encodings are the
  same for every picture (all resized to 1008 px) and cached once; each class phrase is
  encoded once.
* **Trained:** the DETR decoder, the mask decoder and the scoring head (15 M).
* **Per picture and phrase:** queries matched to the phrase's objects on mask dice, box L1
  and score; then focal loss on every query's score, the phrase-presence loss, L1 + GIoU on
  matched boxes, dice + focal on matched masks (DETR's weights). A picture without the
  phrase teaches "none here".
* **Scored** as matched mIoU: predicted and true objects paired one-to-one, and a missed or
  invented object counts 0, so the score cannot be bought with extra masks.

Measured on this Mac (M1, 16 GB, 2026-09-30): 6.2 s per picture for the frozen encoder, 1.1 s
for a training step; 4.7 GB allocated.
"""

from __future__ import annotations

import logging
import random
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from scipy.optimize import linear_sum_assignment
from torch.nn import functional as F
from torchvision.ops import generalized_box_iou

from app.core.config import Settings
from app.core.paths import resolve_model_dir
from app.datasets.rle import rle_decode
from app.finetune.adapter import FinetuneData, FinetuneSettings, TrainingState, memory_budget
from app.ml.training.samples import TrainingSample

logger = logging.getLogger(__name__)

TRAINED = ("detr_decoder.", "mask_decoder.", "dot_product_scoring.")
DECODERS_FILE = "sam3_decoders.pt"
#: 8 % of the machine's memory: the model itself takes 3.4 GB (see the module notes).
CACHE_BUDGET_BYTES = memory_budget(0.08)
SCORE_THRESHOLD = 0.5
#: DETR's loss weights: score, box L1, box GIoU, mask focal, mask dice.
W_CLS, W_L1, W_GIOU, W_MASK, W_DICE = 2.0, 5.0, 2.0, 5.0, 5.0


@dataclass
class Sam3State:
    model: Any
    processor: Any
    device: str
    optimiser: torch.optim.Optimizer
    phrases: tuple[str, ...]
    rng: random.Random
    stop: threading.Event | None = None
    text: dict[str, tuple[Any, torch.Tensor]] = field(default_factory=dict)
    positions: tuple[torch.Tensor, ...] | None = None
    cache: dict[str, tuple[torch.Tensor, ...]] = field(default_factory=dict)
    cached_bytes: int = 0


def _objects(sample: TrainingSample, phrases: tuple[str, ...]) -> dict[str, list[np.ndarray]]:
    found: dict[str, list[np.ndarray]] = {phrase: [] for phrase in phrases}
    for mask in sample.masks:
        found[phrases[mask.class_index]].append(
            rle_decode(list(mask.counts), mask.size).astype(bool)
        )
    return found


def _vision(state: Sam3State, sample: TrainingSample) -> tuple[Any, tuple[int, int]]:
    """The frozen encoder's features (cached) wrapped as the model expects them."""
    from transformers.models.sam3.modeling_sam3 import Sam3VisionEncoderOutput

    with Image.open(sample.path) as opened:
        image = opened.convert("RGB")
    size = (image.height, image.width)
    hidden = state.cache.get(sample.path)
    if hidden is None:
        pixels = state.processor(images=image, return_tensors="pt")["pixel_values"].to(state.device)
        with torch.no_grad():
            out = state.model.get_vision_features(pixel_values=pixels)
        hidden = tuple(t.detach() for t in out.fpn_hidden_states)
        if state.positions is None:
            state.positions = tuple(t.detach() for t in out.fpn_position_encoding)
        stored = tuple(t.to("cpu", torch.float16) for t in hidden)
        nbytes = sum(t.element_size() * t.nelement() for t in stored)
        if state.cached_bytes + nbytes <= CACHE_BUDGET_BYTES:
            state.cache[sample.path], state.cached_bytes = stored, state.cached_bytes + nbytes
    hidden = tuple(t.to(state.device, torch.float32) for t in hidden)
    output = Sam3VisionEncoderOutput(
        fpn_hidden_states=hidden,  # type: ignore[arg-type]
        fpn_position_encoding=state.positions,  # type: ignore[arg-type]
    )
    return output, size


def _boxes(masks: list[np.ndarray], size: tuple[int, int]) -> torch.Tensor:
    """Normalised (cx, cy, w, h) boxes of masks, SAM 3's box format."""
    h, w = size
    rows = []
    for mask in masks:
        ys, xs = np.nonzero(mask)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        rows.append([(x0 + x1) / 2 / w, (y0 + y1) / 2 / h, (x1 - x0) / w, (y1 - y0) / h])
    return torch.tensor(rows, dtype=torch.float32)


def _xyxy(boxes: torch.Tensor) -> torch.Tensor:
    cx, cy, w, h = boxes.unbind(-1)
    return torch.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], -1)


def _focal(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    prob = logits.sigmoid()
    bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    p_t = prob * target + (1 - prob) * (1 - target)
    return (0.25 * (1 - p_t) ** 2 * bce).mean()


def _dice(prob: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    inter = prob.flatten(1) @ target.flatten(1).T
    return 1 - (2 * inter + 1) / (
        prob.flatten(1).sum(1)[:, None] + target.flatten(1).sum(1)[None] + 1
    )


def phrase_loss(out: Any, masks: list[np.ndarray], size: tuple[int, int]) -> torch.Tensor:
    """Match the queries to one phrase's objects, and the loss on that match."""
    logits = out.pred_logits[0].reshape(-1)
    presence = out.presence_logits.reshape(-1)[:1] if out.presence_logits is not None else None

    def presence_loss(value: float) -> torch.Tensor:
        if presence is None:
            return torch.zeros((), device=logits.device)
        return F.binary_cross_entropy_with_logits(presence, torch.full_like(presence, value))

    if not masks:
        return W_CLS * _focal(logits, torch.zeros_like(logits)) + presence_loss(0.0)
    pred_masks = out.pred_masks[0]
    target = torch.from_numpy(np.stack(masks).astype(np.float32))[:, None]
    target = F.interpolate(target, size=pred_masks.shape[-2:], mode="nearest")[:, 0].to(
        logits.device
    )
    true_boxes = _boxes(masks, size).to(logits.device)
    pred_boxes = out.pred_boxes[0]
    with torch.no_grad():
        cost = (
            W_DICE * _dice(pred_masks.sigmoid(), target)
            + W_L1 * torch.cdist(pred_boxes, true_boxes, p=1)
            - W_CLS * logits.sigmoid()[:, None]
        )
    rows, cols = linear_sum_assignment(cost.cpu().numpy())
    rows_t, cols_t = (
        torch.as_tensor(rows, device=logits.device),
        torch.as_tensor(cols, device=logits.device),
    )
    matched = torch.zeros_like(logits)
    matched[rows_t] = 1
    giou = torch.diag(generalized_box_iou(_xyxy(pred_boxes[rows_t]), _xyxy(true_boxes[cols_t])))
    return (
        W_CLS * _focal(logits, matched)
        + presence_loss(1.0)
        + W_L1 * F.l1_loss(pred_boxes[rows_t], true_boxes[cols_t])
        + W_GIOU * (1 - giou).mean()
        + W_MASK * _focal(pred_masks[rows_t], target[cols_t])
        + W_DICE * torch.diag(_dice(pred_masks[rows_t].sigmoid(), target[cols_t])).mean()
    )


def matched_iou(predicted: list[np.ndarray], truths: list[np.ndarray]) -> tuple[float, int]:
    """(sum of IoUs of one-to-one matched pairs, number of objects counted)."""
    count = max(len(predicted), len(truths))
    if count == 0:
        return 0.0, 0
    if not predicted or not truths:
        return 0.0, count
    ious = np.array(
        [
            [np.logical_and(p, t).sum() / max(1, np.logical_or(p, t).sum()) for t in truths]
            for p in predicted
        ]
    )
    rows, cols = linear_sum_assignment(-ious)
    return float(ious[rows, cols].sum()), count


class Sam3Adapter:
    primary_metric = "miou"
    weights_kind = "sam3-decoders"

    def __init__(self, finetune_id: str) -> None:
        self.finetune_id = finetune_id

    def prepare(
        self, data: FinetuneData, settings: FinetuneSettings, app_settings: Settings
    ) -> TrainingState:
        from transformers import Sam3Model, Sam3Processor

        directory = str(resolve_model_dir(self.finetune_id, app_settings))
        device = app_settings.resolved_device
        model = Sam3Model.from_pretrained(directory).to(device)  # type: ignore[arg-type]
        processor = Sam3Processor.from_pretrained(directory)
        for name, parameter in model.named_parameters():
            parameter.requires_grad = name.startswith(TRAINED)
        trainable = [p for p in model.parameters() if p.requires_grad]
        optimiser = torch.optim.AdamW(trainable, lr=settings.learning_rate, weight_decay=1e-4)
        model.eval()
        state = Sam3State(
            model,
            processor,
            device,
            optimiser,
            data.class_names,
            random.Random(settings.seed),
            stop=data.stop,
        )
        for phrase in data.class_names:
            tokens = processor(text=phrase, return_tensors="pt").to(device)
            with torch.no_grad():
                state.text[phrase] = (model.get_text_features(**tokens), tokens["attention_mask"])
        return state

    def _forward(self, state: Sam3State, vision: Any, phrase: str) -> Any:
        text, attention = state.text[phrase]
        return state.model(vision_embeds=vision, text_embeds=text, attention_mask=attention)

    def train_epoch(self, state: TrainingState, data: FinetuneData, epoch: int) -> float:
        assert isinstance(state, Sam3State)
        order = data.train[:]
        state.rng.shuffle(order)
        losses: list[float] = []
        for sample in order:
            if data.stopped:
                break
            vision, size = _vision(state, sample)
            for phrase, masks in _objects(sample, state.phrases).items():
                loss = phrase_loss(self._forward(state, vision, phrase), masks, size)
                state.optimiser.zero_grad(set_to_none=True)
                loss.backward()  # type: ignore[no-untyped-call]
                state.optimiser.step()
                losses.append(float(loss.detach()))
        return sum(losses) / max(1, len(losses))

    def evaluate(self, state: TrainingState, samples: list[TrainingSample]) -> dict[str, float]:
        assert isinstance(state, Sam3State)
        total, count = 0.0, 0
        for sample in samples:
            if state.stop is not None and state.stop.is_set():
                break  # cancelled: the runner discards a partial score
            vision, size = _vision(state, sample)
            for phrase, truths in _objects(sample, state.phrases).items():
                with torch.no_grad():
                    out = self._forward(state, vision, phrase)
                found = state.processor.post_process_instance_segmentation(
                    out, threshold=SCORE_THRESHOLD, target_sizes=[size]
                )[0]
                predicted = [np.asarray(m.cpu(), dtype=bool) for m in found["masks"]]
                part, n = matched_iou(predicted, truths)
                total, count = total + part, count + n
        return {"miou": total / count} if count else {}

    def snapshot(self, state: TrainingState) -> object:
        assert isinstance(state, Sam3State)
        return {
            k: v.detach().clone()
            for k, v in state.model.state_dict().items()
            if k.startswith(TRAINED)
        }

    def restore(self, state: TrainingState, snapshot: object) -> None:
        assert isinstance(state, Sam3State) and isinstance(snapshot, dict)
        state.model.load_state_dict(snapshot, strict=False)

    def save(self, state: TrainingState, directory: Path) -> None:
        assert isinstance(state, Sam3State)
        weights = {
            k: v.detach().cpu()
            for k, v in state.model.state_dict().items()
            if k.startswith(TRAINED)
        }
        torch.save(weights, directory / DECODERS_FILE)


__all__ = ["DECODERS_FILE", "Sam3Adapter", "matched_iou", "phrase_loss"]
