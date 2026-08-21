"""Running a foundation detector as an auto-annotator (doc 42).

The sibling of `expert.py`, and deliberately shaped like it. The difference is what runs:
a head needs a backbone and shares a pass with other heads, while a foundation detector is
self-contained. Everything after the prediction — the verdict, the clamping, the provenance,
the class carried as `prompt` — is identical, because a reviewer should not be able to tell
which produced a box except by looking at where it says it came from.

This is what makes a first run useful: RF-DETR proposes boxes on any image with no prompt
and nothing trained, so a new dataset starts from proposals instead of a blank canvas.

**Concept segmenters come through here too** (doc 45). Grounded SAM produces masks *and*
boxes; the Studio reviews boxes, so it takes the box half — and gets a text-prompted box
proposer that beats Grounding DINO alone, because SAM tightens the extents Grounding DINO
leaves loose. The masks go to the Inference Viewer, where looking is the point.
"""

from __future__ import annotations

import logging

from PIL import Image

from app.core.config import Settings, get_settings
from app.datasets.models import Box, Producer
from app.ml.annotators.proposals import PROPOSED_LABEL, clamp_to_frame
from app.ml.foundation.build import build_foundation
from app.ml.foundation.concept import ConceptSegmenter
from app.ml.foundation.detect import DEFAULT_SCORE_THRESHOLD, RfDetrModel

# Aliased: `Box` in this module is the *stored* annotation, not the four numbers.
from app.ml.inference.results import Box as Box4

logger = logging.getLogger(__name__)

#: The only render hint a box-review surface can show.
ANNOTATABLE_HINT = "boxes"


class FoundationCannotAnnotateError(ValueError):
    """The model works, but what it produces cannot be reviewed as boxes."""


def propose_foundation_boxes(
    image: Image.Image,
    foundation_id: str,
    settings: Settings | None = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    concept: str = "",
) -> list[Box]:
    """Run one foundation detector over one image and return proposed annotations.

    `concept` is required by a concept segmenter and ignored by a detector — an
    RF-DETR predicts its 91 classes whatever you type at it, and silently pretending
    otherwise would be worse than saying so.

    Raises `FoundationUnavailableError` for an unknown id, `ModelNotInstalledError` when
    the weights are absent, and `FoundationCannotAnnotateError` when the model predicts
    something that is not boxes — all three surface unchanged, so the API layer maps them
    to the statuses the other generate routes already use.
    """
    settings = settings or get_settings()
    model = build_foundation(foundation_id, settings)

    if isinstance(model, ConceptSegmenter):
        detections, producer = _from_concept(model, image, concept, score_threshold)
    elif isinstance(model, RfDetrModel):
        detections, producer = _from_detector(model, image, score_threshold)
    else:
        # A depth model is perfectly usable — in the Inference Viewer, where looking is the
        # point. It is not annotatable, because there is nothing here to review it with.
        raise FoundationCannotAnnotateError(
            f"{foundation_id} does not predict boxes, so it cannot be reviewed as "
            f"annotations. Run it in the Inference Viewer instead."
        )

    logger.info(
        "%s proposed %d box(es) on a %dx%d image",
        producer.label,
        len(detections),
        image.width,
        image.height,
    )

    proposals: list[Box] = []
    skipped = 0
    for box, score, class_name in detections:
        clamped = clamp_to_frame(box, image.width, image.height)
        if clamped is None:
            skipped += 1
            continue
        proposals.append(
            Box(
                label=PROPOSED_LABEL,
                provenance="foundation-model",
                x=clamped[0],
                y=clamped[1],
                w=clamped[2],
                h=clamped[3],
                prompt=class_name,
                score=score,
                producer=producer,
            )
        )

    if skipped:
        logger.info("%d proposal(s) fell entirely outside the frame", skipped)
    return proposals


def _from_detector(
    model: RfDetrModel, image: Image.Image, score_threshold: float
) -> tuple[list[tuple[Box4, float, str]], Producer]:
    """A detector's own classes, straight from its prediction."""
    prediction = model.predict(image, score_threshold)
    if prediction.render_hint != ANNOTATABLE_HINT:  # pragma: no cover - guarded by registry
        raise FoundationCannotAnnotateError(f"{model} predicts {prediction.render_hint}")
    # Captured now, not resolved later — the same rule doc 29 set for heads. `provenance`
    # says a foundation model made this; `producer` says which one, so a catalogue change
    # cannot rewrite the history of an existing dataset.
    producer = Producer(
        id=prediction.instance_id,
        label=f"{prediction.head_name} · {prediction.summary}",
    )
    return prediction.detections(), producer


def _from_concept(
    model: ConceptSegmenter, image: Image.Image, concept: str, score_threshold: float
) -> tuple[list[tuple[Box4, float, str]], Producer]:
    """The **box** half of a concept segmenter's output.

    Grounding DINO finds the boxes and SAM refines them into masks; taking the box back out
    is not throwing the segmentation away, it is using the tighter extents SAM implies. The
    phrase that matched becomes the class, exactly as a detector's class name would.
    """
    if not concept.strip():
        raise FoundationCannotAnnotateError(
            f"{model.spec.title} needs a concept — type what you are looking for."
        )
    proposals = model.propose(image, concept, score_threshold)
    detections = [
        (proposal.box, proposal.score, proposal.concept) for proposal in proposals
    ]
    return detections, Producer(id=model.spec.id, label=f"{model.spec.title} · {concept}")


__all__ = [
    "ANNOTATABLE_HINT",
    "FoundationCannotAnnotateError",
    "propose_foundation_boxes",
]
