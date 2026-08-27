"""Calling a foundation model, whatever kind it is.

`build_foundation` answers *which implementation*; this answers *how to call it*. They are
separate because the implementations do not share a signature and deliberately should not:
a detector takes a score threshold, a prompted model takes a concept as well, and a depth
map has nothing to threshold. A uniform signature would mean two of the four accepting an
argument they ignore, which is how a concept ends up silently dropped.

**One capability check, used by every caller.** It lived inside the `/foundation/predict`
handler until doc 68 needed the same dispatch from a worker thread. Two copies would have
been two places to add the next model kind, and the failure of missing one is quiet: the
new model falls through to the no-argument branch, runs happily on an empty prompt, and
returns nothing — which is indistinguishable from "found nothing".
"""

from __future__ import annotations

from PIL import Image

from app.ml.foundation.build import FoundationImplementation
from app.ml.foundation.concept import ConceptSegmenter
from app.ml.foundation.detect import RfDetrModel
from app.ml.foundation.prompt_detect import PromptedDetector
from app.ml.inference.results import Prediction


def predict_with(
    model: FoundationImplementation,
    image: Image.Image,
    concept: str = "",
    score_threshold: float = 0.3,
) -> Prediction:
    """Run ``model`` over one image, passing only what it can use."""
    # Prompted first: a prompted detector reports `detection` too, so an order that checked
    # RF-DETR first would hand Grounding DINO to the branch that drops the concept.
    if isinstance(model, ConceptSegmenter | PromptedDetector):
        return model.predict(image, concept, score_threshold)
    if isinstance(model, RfDetrModel):
        return model.predict(image, score_threshold)
    return model.predict(image)


__all__ = ["predict_with"]
