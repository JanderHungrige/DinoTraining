"""Mask annotators — one contract, several strategies behind it."""

from app.ml.annotators.base import MaskAnnotator, MaskProposal
from app.ml.annotators.registry import (
    ANNOTATORS,
    GROUNDED_SAM,
    SAM3,
    AnnotatorSpec,
    all_annotators,
    get_annotator,
)

__all__ = [
    "ANNOTATORS",
    "GROUNDED_SAM",
    "SAM3",
    "AnnotatorSpec",
    "MaskAnnotator",
    "MaskProposal",
    "all_annotators",
    "get_annotator",
]
