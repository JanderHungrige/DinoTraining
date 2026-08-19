"""Turning an annotator id into a running annotator.

The registry holds *descriptions*; this holds *constructors*. Keeping them apart is what
lets the catalogue list SAM 3 — with its licence, size and gating — before any code exists
to run it.

This module is the **one** sanctioned place that maps an id to an implementation. A
``if annotator_id == "sam3"`` anywhere else is the defect `23-mask-annotator-registry`
describes; here it is a table lookup, and adding an annotator means adding a row.
"""

from __future__ import annotations

from collections.abc import Callable

from app.ml.annotators.base import MaskAnnotator
from app.ml.annotators.grounded_sam import GroundedSamAnnotator
from app.ml.annotators.registry import GROUNDED_SAM, SAM3, get_annotator


class AnnotatorUnavailableError(RuntimeError):
    """The annotator is in the catalogue but has no implementation yet."""


_BUILDERS: dict[str, Callable[[], MaskAnnotator]] = {
    GROUNDED_SAM: GroundedSamAnnotator,
}


def build_annotator(annotator_id: str) -> MaskAnnotator:
    """Construct the annotator for ``annotator_id``.

    Raises ``LookupError`` for an id that is not in the catalogue at all, and
    ``AnnotatorUnavailableError`` for one that is catalogued but not yet implemented —
    two different answers, because the first is a caller mistake and the second is a
    feature that has not shipped.
    """
    if get_annotator(annotator_id) is None:
        raise LookupError(f"Unknown annotator: {annotator_id}")

    builder = _BUILDERS.get(annotator_id)
    if builder is None:
        raise AnnotatorUnavailableError(
            f"{annotator_id} is in the catalogue but cannot be run yet."
            + (
                " SAM 3 support is still being built; Grounded SAM does the same job today."
                if annotator_id == SAM3
                else ""
            )
        )
    return builder()


def implemented_annotator_ids() -> frozenset[str]:
    """Which catalogue entries can actually run. Used by tests and the API."""
    return frozenset(_BUILDERS)
