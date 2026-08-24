"""Running a trained head as an auto-annotator.

This is the flywheel's return leg: a head trained in Wave 2 proposes the boxes that become
the next dataset. It is deliberately thin, because Wave 3 already built everything hard
about it — resolving a head, checking it against the backbone, sharing a backbone pass,
inverting boxes back into the source image's coordinates.

**No coordinate conversion happens here.** ``app/ml/inference/results.py`` defines its box
as xywh in absolute source pixels with a top-left origin, which is exactly the dataset
store's convention, and doc 16 says it chose that convention so this wave could consume it
directly. A conversion in this module would be a bug, not an oversight.
"""

from __future__ import annotations

import logging

from PIL import Image

from app.core.config import Settings, get_settings
from app.datasets.models import Box, Producer
from app.ml.annotators.proposals import PROPOSED_LABEL, clamp_to_frame
from app.ml.heads.registry import RenderHint
from app.ml.inference.compose import run_heads
from app.ml.inference.engine import DEFAULT_SCORE_THRESHOLD

logger = logging.getLogger(__name__)

#: The only render hint that yields something a box-review surface can show. Segmentation
#: and depth heads are *usable* but not *annotatable* — see the wave's open questions.
ANNOTATABLE_HINT: RenderHint = "boxes"

class HeadCannotAnnotateError(ValueError):
    """The head works, but what it produces cannot be reviewed as boxes."""


def propose_boxes(
    image: Image.Image,
    backbone_id: str,
    instance_id: str,
    settings: Settings | None = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> list[Box]:
    """Run one head over one image and return its detections as proposed annotations.

    Raises ``HeadCannotAnnotateError`` when the head's render hint is not ``boxes``,
    ``HeadInstanceNotFoundError`` for an unknown id, and ``BackboneMismatchError`` when the
    head belongs to a different backbone — all three surface to the caller unchanged, so
    the API layer maps them to the same statuses the inference routes already use.
    """
    settings = settings or get_settings()

    # run_heads with one head rather than the single-head path: it is the same resolution
    # and preprocessing logic, and using it here means the generator cannot drift from the
    # viewer in how a head is set up.
    result = run_heads(image, backbone_id, [instance_id], settings, score_threshold)
    prediction = result.predictions[0]

    if prediction.render_hint != ANNOTATABLE_HINT:
        raise HeadCannotAnnotateError(
            f"{prediction.head_name} predicts {prediction.render_hint}, which cannot be "
            f"reviewed as boxes. Choose a detection head, or run this one in the "
            f"Inference Viewer instead."
        )

    detections = prediction.detections()
    # Captured now, not resolved later: the head may be deleted and this annotation must
    # still be able to say what produced it.
    producer = Producer(
        id=prediction.instance_id,
        label=f"{prediction.head_name} · {prediction.summary}",
    )
    logger.info(
        "%s proposed %d box(es) on %s", prediction.head_name, len(detections), backbone_id
    )

    # Clamped to the frame: `decode_ltrb_to_boxes` regresses unbounded distances from a
    # cell centre, so a head can propose a box that leaves the image — and `Box` rejects
    # one, which would fail the save *after* the user had reviewed it. See doc 42.
    proposals: list[Box] = []
    for box, score, class_name in detections:
        clamped = clamp_to_frame(box, image.width, image.height)
        if clamped is None:
            continue
        proposals.append(
            Box(
                label=PROPOSED_LABEL,
                provenance="expert-head",
                x=clamped[0],
                y=clamped[1],
                w=clamped[2],
                h=clamped[3],
                # The class the head predicted, carried as the prompt so it lands in the
                # same field a Grounding DINO proposal uses. One column, one meaning:
                # "what this box was proposed as".
                prompt=class_name,
                score=score,
                producer=producer,
            )
        )
    return proposals
