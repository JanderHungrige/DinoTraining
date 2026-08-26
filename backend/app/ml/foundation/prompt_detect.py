"""Grounding DINO as a foundation model (doc 66).

The Annotation Studio has run it since Wave 1 as a mode of its own. Doc 42 made
self-contained detectors runnable everywhere and doc 45 did the same for the two mask
annotators — and Grounding DINO fell between them, because it is prompted like a mask
annotator and returns boxes like a detector. It was the only model the Studio was built
around that the other two tabs could not run.

**Nothing here is a second Grounding DINO.** `detector.py` has owned prompting, the box
threshold, the per-box matched phrase and the model's xyxy → the store's xywh since Wave 1.
This is that behind the foundation contract, exactly as `ConceptSegmenter` is
`build_annotator` behind the same contract — one loading convention, one conversion, one
place where either could drift.
"""

from __future__ import annotations

import logging
import time

from PIL import Image

from app.core.config import Settings, get_settings
from app.ml.detector import DEFAULT_BOX_THRESHOLD, Detection, detect, load_detector
from app.ml.foundation.registry import FoundationSpec
from app.ml.inference.payloads import source_boxes_payload
from app.ml.inference.results import Prediction

logger = logging.getLogger(__name__)

DEFAULT_SCORE_THRESHOLD = DEFAULT_BOX_THRESHOLD


class PromptedDetector:
    """Text in, boxes out. Satisfies the foundation-model contract."""

    def __init__(self, spec: FoundationSpec, settings: Settings | None = None) -> None:
        self._spec = spec
        self._settings = settings or get_settings()

    @property
    def spec(self) -> FoundationSpec:
        return self._spec

    @property
    def device(self) -> str:
        return str(self._settings.resolved_device)

    def predict(
        self,
        image: Image.Image,
        concept: str = "",
        threshold: float = DEFAULT_SCORE_THRESHOLD,
    ) -> Prediction:
        """Boxes for one image, in that image's own pixel coordinates.

        An empty concept is **not an error** — it is the state before the user has typed
        one — so it returns an empty prediction and loads nothing. Running Grounding DINO
        on `""` matches everything weakly and returns noise that reads as a working
        detector having a bad day, which is worse than returning nothing.
        """
        started = time.perf_counter()

        detections: list[Detection] = []
        if concept.strip():
            detector = load_detector(self._spec.model_id)
            detections = detect(detector, image, concept, box_threshold=threshold)

        payload, class_names = _box_payload(detections)
        elapsed = (time.perf_counter() - started) * 1000.0

        logger.info(
            "%s found %d box(es) for %r on %s in %.0f ms",
            self._spec.id,
            len(detections),
            concept,
            self.device,
            elapsed,
        )

        return Prediction(
            instance_id=self._spec.id,
            head_name=self._spec.title,
            head_type_id=self._spec.id,
            task=self._spec.task,
            render_hint=self._spec.render_hint,
            class_names=class_names,
            payload=payload,
            elapsed_ms=elapsed,
        )


def _box_payload(
    detections: list[Detection],
) -> tuple[dict[str, object], tuple[str, ...]]:
    """Boxes plus the phrase list their class indices point into.

    Grounding DINO answers with a **matched phrase per box**, not a class index, so the
    phrases are collected in first-appearance order and each box carries its position.
    Same mapping `_mask_payload` makes for the segmenter, minus the background class: a box
    payload has no background, so index 0 is a real phrase rather than "nothing here".

    Doing it this way is what makes a phrase keep one colour across every box it matched —
    the renderer colours by class index and has no idea these came from text.
    """
    phrases: list[str] = []
    for detection in detections:
        if detection.text not in phrases:
            phrases.append(detection.text)

    boxes = [(d.x, d.y, d.w, d.h) for d in detections]
    scores = [d.score for d in detections]
    classes = [phrases.index(d.text) for d in detections]

    return source_boxes_payload(boxes, scores, classes), tuple(phrases)


__all__ = ["DEFAULT_SCORE_THRESHOLD", "PromptedDetector"]
