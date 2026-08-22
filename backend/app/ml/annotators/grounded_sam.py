"""Grounded SAM — the ungated implementation of the mask-annotator contract.

A text concept goes to Grounding DINO, whose boxes become SAM 2.1 box prompts, and the
masks come back with the originating boxes alongside. Together these reproduce SAM 3's
contract — a concept in, masks *and* boxes out — under Apache-2.0, with no account, no
token and no access request.

Both stages already existed and neither is re-implemented: `detector.py` owns prompting and
the xyxy→xywh conversion, `segmenter.py` owns SAM 2 and the single device→host hop. This
module is the join, and the join has exactly one interesting decision in it — see below.
"""

from __future__ import annotations

import logging

import numpy as np
from PIL import Image

from app.datasets.rle import rle_bbox, rle_encode
from app.ml.annotators.base import MaskProposal
from app.ml.annotators.registry import GROUNDED_SAM
from app.ml.detector import DEFAULT_BOX_THRESHOLD, Detection, detect, load_detector
from app.ml.segmenter import PromptBox, load_segmenter, segment_boxes

logger = logging.getLogger(__name__)

#: Provenance recorded for every mask this annotator produces. Not `sam3`: the masks came
#: from a different pipeline under a different licence, and "which masks came from the
#: ungated path" is a real question when comparing the two.
PROVENANCE = GROUNDED_SAM


class GroundedSamAnnotator:
    """Text concept in, masks and boxes out. Satisfies `MaskAnnotator`."""

    annotator_id = GROUNDED_SAM

    def __init__(self, detector_id: str | None = None, segmenter_id: str | None = None) -> None:
        self._detector_id = detector_id
        self._segmenter_id = segmenter_id

    def propose(
        self, image: Image.Image, concept: str, *, threshold: float = DEFAULT_BOX_THRESHOLD
    ) -> list[MaskProposal]:
        detector = (
            load_detector(self._detector_id) if self._detector_id else load_detector()
        )
        detections = detect(detector, image, concept, box_threshold=threshold)
        if not detections:
            # No boxes means no prompts, and SAM would otherwise be asked to segment the
            # whole frame. An empty list is the honest answer to "nothing matched".
            logger.info("Grounding DINO found nothing for %r", concept)
            return []

        segmenter = (
            load_segmenter(self._segmenter_id) if self._segmenter_id else load_segmenter()
        )
        masks, scores = segment_boxes(segmenter, image, [_to_xyxy(d) for d in detections])

        return _to_proposals(masks, scores, detections, concept)


def _to_xyxy(detection: Detection) -> PromptBox:
    """The store's xywh to SAM's xyxy.

    The *only* place this conversion happens. `detector.py` converted the model's xyxy
    into the store's xywh precisely once, so nothing downstream has to guess; converting
    back for a prompt is the mirror of that, and doing it anywhere else would give two
    conventions with the same variable names.
    """
    return (
        detection.x,
        detection.y,
        detection.x + detection.w,
        detection.y + detection.h,
    )


def _to_proposals(
    masks: np.ndarray,
    iou_scores: list[float],
    detections: list[Detection],
    concept: str,
) -> list[MaskProposal]:
    """Zip masks back to the boxes that prompted them.

    The three sequences are positional and must stay aligned: dropping an empty mask has
    to drop its box and its score with it, or every later mask is attributed to the wrong
    detection — a mislabel that looks entirely plausible.
    """
    proposals: list[MaskProposal] = []

    for index, detection in enumerate(detections):
        if index >= len(masks):
            # Fewer masks than prompts means the model batched differently than measured.
            # Stopping is better than pairing the remaining boxes with nothing.
            logger.warning(
                "SAM returned %d mask(s) for %d prompt(s); ignoring the remainder",
                len(masks),
                len(detections),
            )
            break

        mask = np.asarray(masks[index], dtype=bool)
        if not mask.any():
            # An all-background mask cannot be stored (the store rejects it) and cannot be
            # reviewed. The box is dropped with it rather than surfacing a mask-less box.
            continue

        counts, size = rle_encode(mask)
        box = rle_bbox(counts, size)
        if box is None:
            continue

        # The detection score is the *concept* match; the IoU is SAM's confidence in the
        # mask. Multiplied so a confident box with a poor mask does not outrank both.
        iou = iou_scores[index] if index < len(iou_scores) else 1.0
        proposals.append(
            MaskProposal(
                counts=counts,
                size=size,
                box=box,
                score=round(float(detection.score) * float(iou), 4),
                # The phrase Grounding DINO matched, not the whole prompt: a prompt of
                # "a cat. a dog." produces per-box phrases and that is what a reviewer
                # needs to see beside each mask.
                concept=detection.text or concept,
            )
        )

    logger.info(
        "Grounded SAM proposed %d mask(s) from %d box(es) for %r",
        len(proposals),
        len(detections),
        concept,
    )
    return proposals
