"""The single registration routine both head sources converge on.

The wave's rule is that first-party defaults and community heads are the same
operation once the bytes are in hand: validate against the backbone capability
descriptor, then persist. That shared half lives here so the trusted and untrusted
callers cannot drift into enforcing different rules — which is exactly what a second
registration path would eventually do.

How the bytes *earn* trust is the callers' business: :mod:`app.ml.heads.install` for
pinned first-party weights, :mod:`app.ml.heads.importer` for community repos.
"""

from __future__ import annotations

import logging

from torch import Tensor

from app.core.config import Settings
from app.ml.backbone import BackboneCapabilities
from app.ml.heads.builders import build_head
from app.ml.heads.instances import HeadInstance, HeadInstanceKind
from app.ml.heads.labels import names_for
from app.ml.heads.registry import HeadTypeSpec, check_compatibility, get_head_type
from app.ml.heads.store import HeadInstanceStore

logger = logging.getLogger(__name__)


class IncompatibleHeadError(ValueError):
    """The head does not fit the chosen backbone, with the reason attached."""


def require_spec(head_type_id: str) -> HeadTypeSpec:
    """Resolve a head type or raise. The registry is the only source of truth."""
    spec = get_head_type(head_type_id)
    if spec is None:
        raise LookupError(f"Unknown head type: {head_type_id}")
    return spec


def require_compatible(spec: HeadTypeSpec, capabilities: BackboneCapabilities) -> None:
    """Compatibility is *explained* on failure, never silently returned as False."""
    verdict = check_compatibility(spec, capabilities)
    if not verdict.compatible:
        raise IncompatibleHeadError(verdict.reason or "Head is not compatible")


def infer_classes(weights: dict[str, Tensor]) -> int:
    """Class count for heads whose builder fixes it (the pretrained defaults).

    Read off the loaded tensor rather than a constant, so the number the picker shows
    is the one actually in the file.
    """
    for key in ("conv_seg.weight", "linear.weight"):
        tensor = weights.get(key)
        if tensor is not None:
            return int(tensor.shape[0])
    return 0  # depth has no classes


def register_head(
    *,
    spec: HeadTypeSpec,
    capabilities: BackboneCapabilities,
    weights: dict[str, Tensor],
    num_classes: int | None,
    kind: HeadInstanceKind,
    name: str,
    source_repo: str,
    source_digest: str,
    settings: Settings,
    config: dict[str, object] | None = None,
) -> HeadInstance:
    """Validate weights against the backbone, then persist.

    The head is *constructed and loaded* rather than shape-checked field by field.
    ``load_state_dict(strict=True)`` is the same check the runtime will perform later,
    so passing here means the head will actually run — whereas a per-field assertion
    only means it will load, which is the failure this feature exists to prevent.
    """
    # Resolved *before* build_head, not after. A trainable head type requires a class
    # count, and an import that omits one (the UI's "auto") otherwise reaches
    # build_head with None and raises — surfacing as a 500 rather than as advice.
    # The weights already carry the answer, so ask them.
    resolved = num_classes if num_classes is not None else infer_classes(weights)
    if spec.trainable and resolved < 1:
        raise IncompatibleHeadError(
            f"{spec.title} needs a class count, and it could not be read from these "
            "weights. Enter how many classes this head predicts and try again."
        )

    # Non-trainable heads carry a fixed upstream label set; build_head rejects a count
    # for them, because accepting one would silently ignore it.
    head = build_head(spec.id, capabilities, resolved if spec.trainable else None)
    try:
        head.load_state_dict(weights, strict=True)
    except (RuntimeError, ValueError) as exc:
        # RuntimeError is what torch raises for a size or key mismatch. Surfaced as
        # incompatibility, because that is what it means to the person who asked.
        raise IncompatibleHeadError(
            f"These weights do not fit {spec.title} on {capabilities.model_id} "
            f"(embed_dim {capabilities.embed_dim}): {exc}"
        ) from exc

    # A pretrained default is a bare `.pth` — weights and nothing else, no `config.json`
    # and no `id2label` — so its class names have to come from the vendored label set its
    # head type names. Without this the store held an empty list and the viewer rendered
    # `class 705` for `passenger car, coach, carriage`: the model was right and could not
    # say so. A trained head has no label set and keeps recording the user's own classes.
    names = names_for(spec.label_set, resolved)

    logger.info("Registering %s head %s for %s", kind, spec.id, capabilities.model_id)
    return HeadInstanceStore(settings).register(
        name=name,
        kind=kind,
        head_type_id=spec.id,
        task=spec.task,
        backbone_id=capabilities.model_id,
        backbone_family=capabilities.family,
        embed_dim=capabilities.embed_dim,
        num_classes=resolved,
        class_names=names,
        weights=weights,
        source_repo=source_repo,
        source_digest=source_digest,
        config=config or {},
    )
