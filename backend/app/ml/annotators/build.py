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
from app.ml.annotators.registry import (
    GROUNDED_SAM,
    GROUNDED_SAM_BASE,
    GROUNDED_SAM_LARGE,
    SAM3,
    AnnotatorSpec,
    get_annotator,
)
from app.ml.annotators.sam3 import Sam3Annotator


class AnnotatorUnavailableError(RuntimeError):
    """The annotator is in the catalogue but has no implementation yet."""


def _grounded_sam(spec: AnnotatorSpec) -> MaskAnnotator:
    """Build a Grounded SAM tier from its own catalogue row.

    The model ids come **off the spec**, never from a table here. That is the whole reason
    the builders take a spec: readiness is computed from `spec.model_ids`, so a builder
    holding ids of its own would let the admin tab report a pipeline ready while this loaded
    something else — a mismatch nothing would report, because both halves would work.
    """
    detector_id, segmenter_id = spec.model_ids
    return GroundedSamAnnotator(spec.id, detector_id, segmenter_id)


#: One row per runnable annotator. Every Grounded SAM tier shares a builder because they
#: differ only in which weights they name, and that difference is data (doc 27).
_BUILDERS: dict[str, Callable[[AnnotatorSpec], MaskAnnotator]] = {
    GROUNDED_SAM: _grounded_sam,
    GROUNDED_SAM_BASE: _grounded_sam,
    GROUNDED_SAM_LARGE: _grounded_sam,
    SAM3: lambda _spec: Sam3Annotator(),
}


def build_annotator(annotator_id: str) -> MaskAnnotator:
    """Construct the annotator for ``annotator_id``.

    Raises ``LookupError`` for an id that is not in the catalogue at all, and
    ``AnnotatorUnavailableError`` for one that is catalogued but not yet implemented —
    two different answers, because the first is a caller mistake and the second is a
    feature that has not shipped.
    """
    spec = get_annotator(annotator_id)
    if spec is None:
        raise LookupError(f"Unknown annotator: {annotator_id}")

    builder = _BUILDERS.get(annotator_id)
    if builder is None:
        raise AnnotatorUnavailableError(
            f"{annotator_id} is in the catalogue but cannot be run yet."
        )
    return builder(spec)


def implemented_annotator_ids() -> frozenset[str]:
    """Which catalogue entries can actually run. Used by tests and the API."""
    return frozenset(_BUILDERS)
