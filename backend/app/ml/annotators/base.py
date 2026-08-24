"""What every mask annotator must satisfy.

One contract, two implementations: `grounded-sam` composes Grounding DINO with SAM 2.1,
`sam3` prompts SAM 3 on a concept directly. They differ in availability far more than in
behaviour — one is Apache-2.0 and ungated, the other needs a token and manual approval — and
this contract is what keeps that difference out of every consumer.

Proposals are plain Python: run lengths, floats and strings, no tensors. Keeping torch out of
this type is what stops a tensor with a live device reference leaking into a response, the
same rule `app/ml/inference/results.py` follows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from PIL import Image

#: (height, width) — COCO's ``size`` order, matching `app/datasets/rle.py`.
Size = tuple[int, int]
#: xywh in absolute source pixels, top-left origin — the dataset store's convention, so a
#: proposal becomes an annotation without conversion.
Box = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class MaskProposal:
    """One proposed mask, ready to be reviewed and stored.

    Carries its box as well as its mask because both annotators produce both, and because
    the review UI places overlays from the box without decoding the RLE.
    """

    counts: list[int]
    size: Size
    box: Box
    score: float
    #: The text concept that produced it. Stored as the annotation's prompt.
    concept: str


@runtime_checkable
class MaskAnnotator(Protocol):
    """Text concept in, masks and boxes out.

    Deliberately narrow. Anything an implementation needs beyond this — a detector stage, a
    token, a device — is its own constructor's business, not the caller's.
    """

    #: Matches the `AnnotatorSpec.id` this implementation serves.
    annotator_id: str

    def propose(
        self, image: Image.Image, concept: str, *, threshold: float = 0.3
    ) -> list[MaskProposal]:
        """Propose masks for one image. Returns an empty list when nothing matches."""
        ...
