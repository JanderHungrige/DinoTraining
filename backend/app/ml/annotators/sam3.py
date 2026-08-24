"""SAM 3 — the gated implementation of the mask-annotator contract.

SAM 3 is *concept-prompted*: a text noun phrase goes straight in and masks come straight
out, with no detector stage. That is the whole difference from `grounded_sam`, which has
to compose two models to reach the same contract — and it is why both satisfy one
interface instead of the caller knowing which it has.

**This module never downloads anything.** `facebook/sam3` is gated behind Meta's manual
approval and is 3.2 GB; the admin tab offers it and the user triggers it, exactly as for
every other model. `load_segmenter` raises `ModelNotInstalledError` when it is absent.

⚠️ **Not yet verified against real weights.** The API shape below is taken from the
installed `transformers` 5.15 — `Sam3Processor.__call__(images=…, text=…)` and
`post_process_instance_segmentation` returning `scores`, `boxes` and binary `masks` — and
the pipeline is covered by stubbed tests. What a stub cannot prove is what SAM 2 taught in
`27-grounded-sam-annotator`: exact output shapes, and that mask tensors arrive on the
model's device. `_to_numpy` in `segmenter.py` covers the second; the first needs a real
run. See doc 30.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from PIL import Image

from app.datasets.rle import rle_bbox, rle_encode
from app.ml.annotators.base import MaskProposal
from app.ml.annotators.registry import SAM3
from app.ml.segmenter import Segmenter, _to_numpy, load_segmenter

logger = logging.getLogger(__name__)

#: Matches Grounding DINO's default so switching annotators does not silently change how
#: much survives.
DEFAULT_THRESHOLD = 0.3

#: SAM 3's own model id in the catalogue.
SAM3_MODEL = "sam3"


class Sam3Annotator:
    """Text concept in, masks and boxes out — in one model. Satisfies `MaskAnnotator`."""

    annotator_id = SAM3

    def __init__(self, model_id: str = SAM3_MODEL) -> None:
        self._model_id = model_id

    def propose(
        self, image: Image.Image, concept: str, *, threshold: float = DEFAULT_THRESHOLD
    ) -> list[MaskProposal]:
        segmenter = load_segmenter(self._model_id)
        instances = segment_concept(segmenter, image, concept, threshold)

        proposals = _to_proposals(instances, concept)
        logger.info(
            "SAM 3 proposed %d mask(s) for %r", len(proposals), concept
        )
        return proposals


def segment_concept(
    segmenter: Segmenter, image: Image.Image, concept: str, threshold: float
) -> dict[str, Any]:
    """Run SAM 3 on one image and one concept.

    Returns the post-processed instance dict: ``scores``, ``boxes`` (xyxy) and ``masks``
    of shape ``(num_instances, height, width)``, already at the image's own size.
    """
    import torch

    text = concept.strip()
    if not text:
        # Prompting SAM 3 with an empty concept asks it to segment nothing in particular.
        raise ValueError("A concept is required — SAM 3 is prompted by text.")

    inputs = segmenter.processor(images=image, text=text, return_tensors="pt").to(
        segmenter.device
    )
    with torch.no_grad():
        outputs = segmenter.model(**inputs)

    results: list[dict[str, Any]] = segmenter.processor.post_process_instance_segmentation(
        outputs, threshold=threshold, target_sizes=[(image.height, image.width)]
    )
    return results[0] if results else {"scores": [], "boxes": [], "masks": []}


def _to_proposals(instances: dict[str, Any], concept: str) -> list[MaskProposal]:
    """Instance dict to proposals, dropping anything with no foreground.

    Masks and scores are positional and are dropped together — the same rule
    `grounded_sam` follows, and for the same reason: a partial drop attributes every later
    mask to the wrong score, which looks entirely plausible.
    """
    masks = _to_numpy(instances["masks"]) if len(instances.get("masks", [])) else None
    if masks is None or masks.size == 0:
        return []

    scores = [float(value) for value in _to_numpy(instances["scores"]).reshape(-1)]
    proposals: list[MaskProposal] = []

    for index in range(masks.shape[0]):
        mask = np.asarray(masks[index], dtype=bool)
        if mask.ndim == 3:
            # Some post-processors keep a singleton candidate axis; SAM 2 does.
            mask = mask[0]
        if not mask.any():
            continue

        counts, size = rle_encode(mask)
        box = rle_bbox(counts, size)
        if box is None:
            continue

        proposals.append(
            MaskProposal(
                counts=counts,
                size=size,
                box=box,
                score=round(scores[index] if index < len(scores) else 1.0, 4),
                # One concept per call, so every mask carries it — unlike Grounded SAM,
                # where Grounding DINO reports which phrase matched each box.
                concept=concept,
            )
        )
    return proposals
