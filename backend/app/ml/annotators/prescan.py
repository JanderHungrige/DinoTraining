"""Finding the images worth annotating, before annotating any of them (doc 53).

A rail sequence has 400 frames and a person in 30 of them. Reviewing that folder means
pressing Next 370 times to confirm nothing is there — which is the work the app exists to
remove, being done by hand.

Prescan runs the **same model the session is about to propose with**, over the whole folder,
and reports which images it found the wanted labels in. The Studio then offers those first.
That the model is the same one matters: prescanning with a different model would filter on
one opinion and annotate on another, and every disagreement would look like a bug in the
proposer.

**A miss is not recorded.** The store never learns that an image was scanned and found
empty. A model's silence is not an annotation, and writing one would put a judgement in the
dataset that nobody made — and would teach the next training run that those images are
background, on the authority of a model that may simply be wrong. The user can always turn
the filter off and see every image; that is the escape hatch, and it is deliberate that it
does not need undoing anything.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from PIL import Image

from app.core.config import Settings, get_settings
from app.datasets.models import Box

logger = logging.getLogger(__name__)

PrescanKind = Literal["prompt", "head", "foundation"]

DEFAULT_SCORE_THRESHOLD = 0.3


@dataclass(frozen=True, slots=True)
class PrescanConfig:
    """One scan. Immutable, so a job's report cannot describe a config it did not run."""

    kind: PrescanKind
    image_paths: tuple[str, ...]
    #: What to look for. **Empty means "any detection counts"**, which is the right default
    #: for a single-class head — asking the user to retype the only class it knows would be
    #: a question with one answer.
    labels: tuple[str, ...] = ()
    score_threshold: float = DEFAULT_SCORE_THRESHOLD
    #: prompt
    model_id: str = ""
    prompt: str = ""
    text_threshold: float = 0.25
    #: head
    backbone_id: str = ""
    instance_id: str = ""
    #: foundation
    foundation_id: str = ""
    concept: str = ""

    def __post_init__(self) -> None:
        if not self.image_paths:
            raise ValueError("Nothing to scan — no images were given")
        if not 0.0 <= self.score_threshold <= 1.0:
            raise ValueError(f"score_threshold must be in [0, 1], got {self.score_threshold}")
        required = {
            "prompt": ("model_id", "prompt"),
            "head": ("backbone_id", "instance_id"),
            "foundation": ("foundation_id",),
        }[self.kind]
        for field_name in required:
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"A {self.kind} scan needs {field_name}")


@dataclass(frozen=True, slots=True)
class PrescanHit:
    """One image the scan kept, and why."""

    path: str
    boxes: int
    best_score: float
    labels: tuple[str, ...]


def matches(box: Box, labels: tuple[str, ...]) -> bool:
    """Does this box count as one of the labels being looked for?

    Matching is **case-insensitive and either-way substring**, not equality, because the
    class a proposer reports is not always the phrase the user typed. Grounding DINO
    re-segments its prompt — ask for `chess piece` and a box comes back labelled `chess` —
    and a fine-tuned detector's class names come from whatever the dataset called them.
    Exact matching would silently return zero hits and read as "the model found nothing".

    Forgiving in the direction that costs least: a false hit shows the user an image they
    then reject in one click, while a false miss hides an image they never learn existed.
    """
    if not labels:
        return True
    found = (box.prompt or "").strip().lower()
    if not found:
        return False
    return any(
        wanted in found or found in wanted
        for wanted in (label.strip().lower() for label in labels)
        if wanted
    )


def scan_boxes(boxes: list[Box], config: PrescanConfig) -> PrescanHit | None:
    """Turn one image's proposals into a hit, or None when nothing qualified."""
    kept = [
        box
        for box in boxes
        if (box.score is None or box.score >= config.score_threshold)
        and matches(box, config.labels)
    ]
    if not kept:
        return None
    return PrescanHit(
        path="",
        boxes=len(kept),
        best_score=max((box.score or 0.0) for box in kept),
        labels=tuple(sorted({(box.prompt or "").strip() for box in kept if box.prompt})),
    )


def propose_for(
    image: Image.Image, config: PrescanConfig, settings: Settings | None = None
) -> list[Box]:
    """The boxes the session's own proposer would produce for this image.

    Imported inside the function on purpose: the three proposers pull in torch, the model
    registry and the annotator catalogue between them, and this module is imported by the
    API layer at startup.
    """
    settings = settings or get_settings()
    if config.kind == "head":
        from app.ml.annotators.expert import propose_boxes

        return propose_boxes(
            image, config.backbone_id, config.instance_id, settings, config.score_threshold
        )
    if config.kind == "foundation":
        from app.ml.annotators.foundation import propose_foundation_boxes

        # Boxes only. A prescan asks "is the thing in this picture?" over hundreds of
        # images and keeps a count; the masks a concept segmenter also produces would be
        # decoded and thrown away once per image for no answer they could give (doc 61).
        return [
            proposal.box
            for proposal in propose_foundation_boxes(
                image, config.foundation_id, settings, config.score_threshold, config.concept
            )
        ]
    return _prompt_boxes(image, config)


def _prompt_boxes(image: Image.Image, config: PrescanConfig) -> list[Box]:
    from app.ml.detector import detect, load_detector

    detector = load_detector(config.model_id)
    detections = detect(
        detector, image, config.prompt, config.score_threshold, config.text_threshold
    )
    return [
        Box(
            label="positive",
            provenance="grounding-dino",
            x=d.x,
            y=d.y,
            w=d.w,
            h=d.h,
            score=min(d.score, 1.0),
            prompt=d.text or config.prompt,
        )
        for d in detections
    ]


__all__ = [
    "DEFAULT_SCORE_THRESHOLD",
    "PrescanConfig",
    "PrescanHit",
    "PrescanKind",
    "matches",
    "propose_for",
    "scan_boxes",
]
