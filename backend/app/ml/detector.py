"""Grounding DINO inference.

The model is loaded once per (model_id, device) and cached. Loading takes seconds and
hundreds of megabytes; per-request loading would make the annotation loop unusable.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

from PIL import Image

from app.core.config import get_settings
from app.core.paths import is_installed, resolve_model_dir
from app.ml.registry import ModelSpec, get_model

logger = logging.getLogger(__name__)

DEFAULT_DETECTOR = "grounding-dino-tiny"
DEFAULT_BOX_THRESHOLD = 0.3
DEFAULT_TEXT_THRESHOLD = 0.25


class ModelNotInstalledError(LookupError):
    """The requested detector has not been downloaded yet."""


@dataclass(frozen=True, slots=True)
class Detection:
    """One proposal, already in the dataset store's convention (xywh, absolute px)."""

    x: float
    y: float
    w: float
    h: float
    score: float
    text: str


@dataclass
class Detector:
    """A loaded Grounding DINO processor + model pair."""

    model_id: str
    device: str
    processor: Any
    model: Any


_cache: dict[tuple[str, str], Detector] = {}
_lock = threading.Lock()


def normalise_prompt(prompt: str) -> str:
    """Grounding DINO expects lowercase phrases ending in a period.

    Wording is left alone — silently rewriting a user's prompt makes it impossible to
    tune. Only casing and the trailing separator are normalised.
    """
    text = prompt.strip().lower()
    if not text:
        raise ValueError("Prompt must not be empty")
    return text if text.endswith(".") else f"{text}."


def _require_spec(model_id: str) -> ModelSpec:
    spec = get_model(model_id)
    if spec is None:
        raise LookupError(f"Unknown model: {model_id}")
    if spec.kind != "detector":
        raise ValueError(f"{model_id} is not a detector")
    return spec


def load_detector(model_id: str = DEFAULT_DETECTOR) -> Detector:
    """Load (or reuse) a detector. Never downloads — that is the Admin tab's job."""
    spec = _require_spec(model_id)
    device = get_settings().resolved_device
    key = (spec.id, device)

    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached

        directory = resolve_model_dir(spec.id)
        if not is_installed(directory):
            # No implicit download: a 690 MB fetch triggered by a keystroke in the
            # Studio is not something to do behind the user's back.
            raise ModelNotInstalledError(spec.id)

        logger.info("Loading %s on %s", spec.id, device)
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        # transformers ships untyped factory methods; this pair is the library boundary.
        processor = AutoProcessor.from_pretrained(str(directory))  # type: ignore[no-untyped-call]
        model = AutoModelForZeroShotObjectDetection.from_pretrained(str(directory)).to(device)
        model.eval()

        detector = Detector(model_id=spec.id, device=device, processor=processor, model=model)
        _cache[key] = detector
        logger.info("Loaded %s", spec.id)
        return detector


def detect(
    detector: Detector,
    image: Image.Image,
    prompt: str,
    box_threshold: float = DEFAULT_BOX_THRESHOLD,
    text_threshold: float = DEFAULT_TEXT_THRESHOLD,
) -> list[Detection]:
    """Run the detector and return boxes in absolute pixels, xywh, top-left origin."""
    import torch

    text = normalise_prompt(prompt)
    inputs = detector.processor(images=image, text=text, return_tensors="pt").to(detector.device)

    with torch.no_grad():
        outputs = detector.model(**inputs)

    results = detector.processor.post_process_grounded_object_detection(
        outputs,
        inputs["input_ids"],
        threshold=box_threshold,
        text_threshold=text_threshold,
        target_sizes=[(image.height, image.width)],
    )[0]

    return _to_detections(results)


def _to_detections(results: dict[str, Any]) -> list[Detection]:
    """Convert the model's xyxy output to the store's xywh convention.

    This conversion happens exactly once, here, so nothing downstream has to guess
    which convention the numbers are in.
    """
    labels = results.get("text_labels", results.get("labels", []))
    detections: list[Detection] = []

    for box, score, label in zip(results["boxes"], results["scores"], labels, strict=False):
        x_min, y_min, x_max, y_max = (float(value) for value in box)
        width, height = x_max - x_min, y_max - y_min
        if width <= 0 or height <= 0:
            continue
        detections.append(
            Detection(
                x=round(max(x_min, 0.0), 2),
                y=round(max(y_min, 0.0), 2),
                w=round(width, 2),
                h=round(height, 2),
                score=round(float(score), 4),
                text=str(label),
            )
        )
    return detections


def clear_cache() -> None:
    """Drop loaded models. For tests, and for freeing memory after a device change."""
    with _lock:
        _cache.clear()
