"""Maps a head-type id to its module constructor.

Separate from :mod:`app.ml.heads.registry` because the registry must stay torch-free —
it is read by the API on every request. This module is imported only when a head is
actually built.

Every spec in the registry must appear here. A spec with no builder fails the moment a
user selects it in the trainer, which is far too late; a test asserts the two tables
stay in sync.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from torch import nn

from app.ml.heads.modules import (
    ClassificationHead,
    DepthHead,
    DetectionHead,
    SegmentationHead,
)
from app.ml.heads.registry import get_head_type

if TYPE_CHECKING:
    from app.ml.backbone import BackboneCapabilities

#: (capabilities, num_classes) -> module. num_classes is None only for depth.
HeadBuilder = Callable[["BackboneCapabilities", int | None], nn.Module]


def _classifier(capabilities: BackboneCapabilities, num_classes: int | None) -> nn.Module:
    assert num_classes is not None  # guaranteed by build_head's validation
    return ClassificationHead(embed_dim=capabilities.embed_dim, num_classes=num_classes)


def _detector(capabilities: BackboneCapabilities, num_classes: int | None) -> nn.Module:
    assert num_classes is not None
    return DetectionHead(
        embed_dim=capabilities.embed_dim,
        num_classes=num_classes,
        patch_size=capabilities.patch_size,
    )


def _segmenter(capabilities: BackboneCapabilities, num_classes: int | None) -> nn.Module:
    assert num_classes is not None
    return SegmentationHead(embed_dim=capabilities.embed_dim, num_classes=num_classes)


def _depth(capabilities: BackboneCapabilities, num_classes: int | None) -> nn.Module:
    return DepthHead(embed_dim=capabilities.embed_dim)


HEAD_BUILDERS: dict[str, HeadBuilder] = {
    "linear-classifier": _classifier,
    "dense-detector": _detector,
    "linear-segmenter": _segmenter,
    "linear-depth": _depth,
}


def build_head(
    head_type_id: str, capabilities: BackboneCapabilities, num_classes: int | None
) -> nn.Module:
    """Construct a head for this backbone.

    Validation lives here rather than in each module so that every construction path
    gets it — the modules themselves are only reachable through this function in
    production code.
    """
    spec = get_head_type(head_type_id)
    if spec is None:
        raise LookupError(f"Unknown head type: {head_type_id}")

    builder = HEAD_BUILDERS.get(head_type_id)
    if builder is None:  # pragma: no cover - the sync test makes this unreachable
        raise LookupError(f"No builder registered for head type: {head_type_id}")

    if spec.trainable:
        if num_classes is None:
            raise ValueError(f"{head_type_id} is trainable and needs num_classes")
        if num_classes < 1:
            raise ValueError(f"{head_type_id}: num_classes must be >= 1, got {num_classes}")
    elif num_classes is not None:
        # Passing classes to depth means the caller has confused two head types; taking
        # it silently would build a head that ignores an argument the caller thought mattered.
        raise ValueError(f"{head_type_id} has no classes — pass num_classes=None")

    head = builder(capabilities, num_classes)
    # Explicit rather than assumed: the backbone is frozen in 07, and heads are the
    # only thing that trains. Both halves are asserted in tests.
    head.requires_grad_(True)
    return head
