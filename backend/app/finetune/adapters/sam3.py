"""Fine-tuning SAM 3 on the user's phrases and outlines (doc 96).

SAM 3 is prompted by a noun phrase and returns every instance of it: a DETR-style set of
200 queries, each with a mask, a box and a score, plus a presence score for the phrase.
Training it therefore needs what DETR needs, which `transformers` does not ship: a
Hungarian match between queries and ground-truth objects, then losses on the match.

* **Frozen:** the image and text encoders (825 M of 840 M parameters). Image features are
  cached per picture (fp16, CPU, within the `cache_share` budget); position encodings are the
  same for every picture (all resized to 1008 px) and cached once; each class phrase is
  encoded once.
* **Trained:** the DETR decoder, the mask decoder and the scoring head (15 M).
* **Per picture and phrase:** queries matched to the phrase's objects on mask dice, box L1
  and score; then focal loss on every query's score, the phrase-presence loss, L1 + GIoU on
  matched boxes, dice + focal on matched masks (DETR's weights, settings since doc 99;
  `sam3_loss`). A picture without the phrase teaches "none here".
* **Scored** as matched mIoU: predicted and true objects paired one-to-one, and a missed or
  invented object counts 0, so the score cannot be bought with extra masks.

Measured on this Mac (M1, 16 GB, 2026-09-30): 6.2 s per picture for the frozen encoder, 1.1 s
for a training step; 4.7 GB allocated.
"""

from __future__ import annotations

import logging
import random
import threading
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image

from app.core.config import Settings
from app.core.paths import resolve_model_dir
from app.datasets.rle import rle_decode
from app.finetune.adapter import (
    FinetuneData,
    FinetuneSettings,
    TrainingState,
    memory_budget,
    param,
)
from app.finetune.adapters.sam3_loss import FAMILY, LossWeights, matched_iou, phrase_loss
from app.finetune.adapters.sam3_queries import QuerySettings, describe, plan_queries
from app.finetune.phrase_data import PhraseTable, load_phrase_table
from app.ml.training.samples import TrainingSample

logger = logging.getLogger(__name__)

TRAINED = ("detr_decoder.", "mask_decoder.", "dot_product_scoring.")
DECODERS_FILE = "sam3_decoders.pt"


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
    weights: LossWeights = field(default_factory=LossWeights)
    #: Doc 108: phrases, checks and negatives, and what training used of them.
    table: PhraseTable = field(default_factory=PhraseTable)
    queries: QuerySettings = field(default_factory=QuerySettings)
    counts: Counter[str] = field(default_factory=Counter)
    rounds: int = 0
    #: The feature cache's share of memory (doc 99; 8 %, as the model takes 3.4 GB).
    cache_bytes: int = 0
    score_threshold: float = 0.5
    cache: dict[str, tuple[torch.Tensor, ...]] = field(default_factory=dict)
    cached_bytes: int = 0


def _decoded(sample: TrainingSample) -> list[np.ndarray]:
    return [rle_decode(list(m.counts), m.size).astype(bool) for m in sample.masks]


def query_settings(settings: FinetuneSettings) -> QuerySettings:
    """Doc 108's negatives and wordings, from the catalogue (doc 99)."""
    return QuerySettings(
        num_negatives=int(param(settings, FAMILY, "num_negatives")),
        num_cross_negatives=int(param(settings, FAMILY, "num_cross_negatives")),
        all_variations=bool(param(settings, FAMILY, "all_variations")),
        rejected_as_negatives=bool(param(settings, FAMILY, "rejected_as_negatives")),
    )


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
        if state.cached_bytes + nbytes <= state.cache_bytes:
            state.cache[sample.path], state.cached_bytes = stored, state.cached_bytes + nbytes
    hidden = tuple(t.to(state.device, torch.float32) for t in hidden)
    output = Sam3VisionEncoderOutput(
        fpn_hidden_states=hidden,  # type: ignore[arg-type]
        fpn_position_encoding=state.positions,  # type: ignore[arg-type]
    )
    return output, size


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
        optimiser = torch.optim.AdamW(
            trainable,
            lr=settings.learning_rate,
            weight_decay=param(settings, FAMILY, "weight_decay"),
        )
        model.eval()
        state = Sam3State(
            model,
            processor,
            device,
            optimiser,
            data.class_names,
            random.Random(settings.seed),
            stop=data.stop,
            weights=LossWeights.from_settings(settings),
            cache_bytes=memory_budget(param(settings, FAMILY, "cache_share")),
            score_threshold=param(settings, FAMILY, "score_threshold"),
            table=load_phrase_table(data.dataset_ids, app_settings),
            queries=query_settings(settings),
        )
        return state

    def _forward(self, state: Sam3State, vision: Any, phrase: str) -> Any:
        if phrase not in state.text:
            # Encoded once per wording; variations, look-alikes and generic negatives arrive
            # as they are planned (doc 108).
            tokens = state.processor(text=phrase, return_tensors="pt").to(state.device)
            with torch.no_grad():
                features = state.model.get_text_features(**tokens)
            state.text[phrase] = (features, tokens["attention_mask"])
        text, attention = state.text[phrase]
        return state.model(vision_embeds=vision, text_embeds=text, attention_mask=attention)

    def notes(self, state: TrainingState) -> list[str]:
        """What the queries were, for the job (doc 108)."""
        assert isinstance(state, Sam3State)
        return [describe(state.counts, state.rounds)] if state.rounds else []

    def train_epoch(self, state: TrainingState, data: FinetuneData, epoch: int) -> float:
        assert isinstance(state, Sam3State)
        order = data.train[:]
        state.rng.shuffle(order)
        state.rounds += 1
        losses: list[float] = []
        for sample in order:
            if data.stopped:
                break
            queries = plan_queries(sample, state.phrases, state.table, state.queries, state.rng)
            if not queries:
                continue
            vision, size = _vision(state, sample)
            decoded = _decoded(sample)
            for query in queries:
                state.counts[query.kind] += 1
                out = self._forward(state, vision, query.text)
                masks = [decoded[i] for i in query.masks]
                loss = phrase_loss(out, masks, size, state.weights)
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
            queries = plan_queries(
                sample, state.phrases, state.table, state.queries, state.rng, evaluation=True
            )
            if not queries:
                continue
            vision, size = _vision(state, sample)
            decoded = _decoded(sample)
            for query in queries:
                truths = [decoded[i] for i in query.masks]
                with torch.no_grad():
                    out = self._forward(state, vision, query.text)
                found = state.processor.post_process_instance_segmentation(
                    out, threshold=state.score_threshold, target_sizes=[size]
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
