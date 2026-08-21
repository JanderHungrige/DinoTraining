"""Running a foundation detector as an auto-annotator (doc 42).

The sibling of `expert.py`, and deliberately shaped like it. The difference is what runs:
a head needs a backbone and shares a pass with other heads, while a foundation detector is
self-contained. Everything after the prediction — the verdict, the clamping, the provenance,
the class carried as `prompt` — is identical, because a reviewer should not be able to tell
which produced a box except by looking at where it says it came from.

This is what makes a first run useful: RF-DETR proposes boxes on any image with no prompt
and nothing trained, so a new dataset starts from proposals instead of a blank canvas.
"""

from __future__ import annotations

import logging

from PIL import Image

from app.core.config import Settings, get_settings
from app.datasets.models import Box, Producer
from app.ml.annotators.proposals import PROPOSED_LABEL, clamp_to_frame
from app.ml.foundation.build import build_foundation
from app.ml.foundation.detect import DEFAULT_SCORE_THRESHOLD, RfDetrModel

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
) -> list[Box]:
    """Run one foundation detector over one image and return proposed annotations.

    Raises `FoundationUnavailableError` for an unknown id, `ModelNotInstalledError` when
    the weights are absent, and `FoundationCannotAnnotateError` when the model predicts
    something that is not boxes — all three surface unchanged, so the API layer maps them
    to the statuses the other generate routes already use.
    """
    settings = settings or get_settings()
    model = build_foundation(foundation_id, settings)

    if not isinstance(model, RfDetrModel):
        # A depth model is perfectly usable — in the Inference Viewer, where looking is the
        # point. It is not annotatable, because there is nothing here to review it with.
        raise FoundationCannotAnnotateError(
            f"{foundation_id} does not predict boxes, so it cannot be reviewed as "
            f"annotations. Run it in the Inference Viewer instead."
        )

    prediction = model.predict(image, score_threshold)
    if prediction.render_hint != ANNOTATABLE_HINT:  # pragma: no cover - guarded above
        raise FoundationCannotAnnotateError(f"{foundation_id} predicts {prediction.render_hint}")

    detections = prediction.detections()
    # Captured now, not resolved later — the same rule doc 29 set for heads. `provenance`
    # says a foundation model made this; `producer` says which one, so a catalogue change
    # cannot rewrite the history of an existing dataset.
    producer = Producer(
        id=prediction.instance_id,
        label=f"{prediction.head_name} · {prediction.summary}",
    )
    logger.info(
        "%s proposed %d box(es) on a %dx%d image",
        prediction.head_name,
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


__all__ = [
    "ANNOTATABLE_HINT",
    "FoundationCannotAnnotateError",
    "propose_foundation_boxes",
]
