"""Concept-prompted segmentation as a foundation model (doc 45).

Grounded SAM and SAM 3 already existed as `MaskAnnotator`s, reachable only from the Dataset
Generator. They are foundation models by every definition this project uses — self-contained,
needing no trained head — so this exposes them through the same contract, and they appear in
the Inference Viewer and the Annotation Studio without either learning a new concept.

**The two halves go to different places, on purpose.** Grounding DINO finds boxes and SAM
turns them into masks, so the pipeline produces both:

* the **Inference Viewer** takes the masks, because looking is the point there;
* the **Annotation Studio** takes the boxes, because that is what it reviews. A
  text-prompted box proposer that is *better* than Grounding DINO alone, since SAM tightens
  the extents Grounding DINO leaves loose.

Wave 5 declined mask review in the Studio — its promise is hand-refinement and there is no
mask editor — and that decision stands. Nothing here reverses it.
"""

from __future__ import annotations

import logging
import time

import numpy as np
from PIL import Image

from app.core.config import Settings, get_settings
from app.datasets.rle import rle_decode
from app.ml.annotators.base import MaskProposal
from app.ml.annotators.build import build_annotator
from app.ml.foundation.registry import FoundationSpec
from app.ml.inference.payloads import MAX_PNG_CLASSES, encode_class_map
from app.ml.inference.results import Prediction

logger = logging.getLogger(__name__)

DEFAULT_SCORE_THRESHOLD = 0.3


class ConceptSegmenter:
    """A mask annotator, wearing the foundation-model contract."""

    def __init__(self, spec: FoundationSpec, settings: Settings | None = None) -> None:
        self._spec = spec
        self._settings = settings or get_settings()

    @property
    def spec(self) -> FoundationSpec:
        return self._spec

    @property
    def device(self) -> str:
        return str(self._settings.resolved_device)

    def propose(
        self, image: Image.Image, concept: str, threshold: float = DEFAULT_SCORE_THRESHOLD
    ) -> list[MaskProposal]:
        """The raw proposals — masks *and* boxes. Both callers start here."""
        annotator = build_annotator(str(self._spec.annotator_id))
        return annotator.propose(image, concept, threshold=threshold)

    def predict(
        self, image: Image.Image, concept: str = "", threshold: float = DEFAULT_SCORE_THRESHOLD
    ) -> Prediction:
        """Masks for one image, shaped exactly as a segmentation head's are.

        An empty concept is not an error — it is the state before the user has typed one —
        so it returns an empty prediction rather than running a model over nothing.
        """
        started = time.perf_counter()
        proposals = self.propose(image, concept, threshold) if concept.strip() else []
        payload, class_names = _mask_payload(proposals, image.height, image.width)
        elapsed = (time.perf_counter() - started) * 1000.0

        logger.info(
            "%s proposed %d mask(s) for %r in %.0f ms",
            self._spec.id,
            len(proposals),
            concept,
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


def _mask_payload(
    proposals: list[MaskProposal], height: int, width: int
) -> tuple[dict[str, object], tuple[str, ...]]:
    """Composite RLE proposals into the index map doc 20 already knows how to draw.

    Class 0 is background, so a phrase's index is its position **plus one**. Later masks
    paint over earlier ones where they overlap — the same last-writer-wins a segmentation
    head's argmax produces, so the renderer cannot tell the two apart.

    The indices are **spread across the byte range** before they become pixels — see
    `encode_class_map`. This map is the fragile one: with a single phrase its classes are 0
    and 1, adjacent bytes, and a webview that dithers the PNG on the way in turns half the
    background into the phrase. That was the green speckle over the whole frame.
    """
    # Distinct concepts, in the order they first appear, so a phrase keeps one colour.
    phrases: list[str] = []
    for proposal in proposals:
        if proposal.concept not in phrases:
            phrases.append(proposal.concept)
    if len(phrases) + 1 > MAX_PNG_CLASSES:  # pragma: no cover - needs 255 distinct phrases
        raise ValueError(f"{len(phrases)} concepts exceed the PNG transport's limit")

    indices = np.zeros((height, width), dtype=np.uint8)
    for proposal in proposals:
        mask = rle_decode(proposal.counts, proposal.size)
        indices[mask] = phrases.index(proposal.concept) + 1

    present = sorted({int(value) for value in np.unique(indices)})
    mask_png, stride = encode_class_map(indices, len(phrases))
    return (
        {
            "mask_png": mask_png,
            #: Pixel value = class index × this. One phrase makes it 255, so background and
            #: object sit at opposite ends of the byte instead of one apart.
            "class_stride": stride,
            "present_classes": present,
            "height": height,
            "width": width,
        },
        ("background", *phrases),
    )


__all__ = ["DEFAULT_SCORE_THRESHOLD", "ConceptSegmenter"]
