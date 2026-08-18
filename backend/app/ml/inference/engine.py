"""Compose Wave 2's pieces into one prediction, in the right order.

Almost nothing here is new. The value is the *ordering* — preprocessing derived from the
(backbone, head) pair, features from the frozen backbone, decode through the registry,
then geometry inverted back onto the user's image. Get the order wrong and each step
still succeeds; only the numbers are wrong.

Nothing in this module branches on task. Everything task-shaped is looked up:
``get_head_type`` for the contract, ``decode_for`` for the decoder, ``render_hint`` for
what the payload should be.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import torch
from PIL import Image

from app.core.config import Settings
from app.ml.backbone import Backbone, BackboneFeatures
from app.ml.heads.builders import build_head
from app.ml.heads.decode import decode_for
from app.ml.heads.instances import HeadInstance
from app.ml.heads.registry import HeadTypeSpec, get_head_type
from app.ml.heads.store import HeadInstanceStore
from app.ml.inference.payloads import build_payload
from app.ml.inference.results import Prediction
from app.ml.preprocess import GeometryTransform, PreprocessPlan

logger = logging.getLogger(__name__)

#: Below this the box is noise. Tunable per call; this is what the viewer defaults to.
DEFAULT_SCORE_THRESHOLD = 0.3


class BackboneMismatchError(ValueError):
    """The head was registered for a different backbone than the one requested."""


def _require_instance(instance_id: str, settings: Settings) -> HeadInstance:
    return HeadInstanceStore(settings).get(instance_id)


def _require_spec(instance: HeadInstance) -> HeadTypeSpec:
    spec = get_head_type(instance.head_type_id)
    if spec is None:
        # Reachable only if a head type is removed from the registry while instances
        # trained against it survive in the database.
        raise LookupError(
            f"Head {instance.id} has head type {instance.head_type_id!r}, "
            "which is no longer in the registry."
        )
    return spec


def load_head(instance: HeadInstance, backbone: Backbone, settings: Settings) -> torch.nn.Module:
    """Build the module and load its stored weights onto the backbone's device."""
    spec = _require_spec(instance)
    capabilities = backbone.capabilities

    head = build_head(
        spec.id, capabilities, instance.num_classes if spec.trainable else None
    )
    head.load_state_dict(HeadInstanceStore(settings).load_weights(instance.id), strict=True)
    # The caller moves the head, matching runner.py:135. build_head returns a CPU
    # module while load_backbone honours the resolved device, and the mismatch raises
    # at the first matmul rather than at load — invisible until a real forward pass.
    head.to(backbone.device)
    head.eval()
    return head


@dataclass(frozen=True, slots=True)
class ResolvedHead:
    """A head instance and its registry contract, checked against the backbone."""

    instance: HeadInstance
    spec: HeadTypeSpec


def resolve_head(instance_id: str, backbone_id: str, settings: Settings) -> ResolvedHead:
    """Look a head up and confirm it belongs to this backbone.

    Separated from running it so a caller with several heads can resolve them all before
    paying for a single forward pass — see :mod:`app.ml.inference.compose`.
    """
    instance = _require_instance(instance_id, settings)
    if instance.backbone_id != backbone_id:
        raise BackboneMismatchError(
            f"{instance.name} was registered for {instance.backbone_id}, "
            f"but {backbone_id} was requested. Select {instance.backbone_id} to run it."
        )
    return ResolvedHead(instance=instance, spec=_require_spec(instance))


def predict_from_features(
    resolved: ResolvedHead,
    features: BackboneFeatures,
    transform: GeometryTransform,
    plan: PreprocessPlan,
    backbone: Backbone,
    settings: Settings,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> Prediction:
    """One head's work, given features somebody else paid for.

    ``elapsed_ms`` measures *this* — forward, decode, inversion — and deliberately not
    the backbone pass, which may be shared with other heads. The total is reported by
    the caller; the gap between the two is the saving. See doc 18.
    """
    started = time.perf_counter()
    head = load_head(resolved.instance, backbone, settings)

    with torch.no_grad():
        outputs = head(features)

    decoded = decode_for(resolved.spec)(outputs, plan.patch_size)
    payload = build_payload(resolved.spec, decoded, transform, plan.size, score_threshold)
    elapsed = (time.perf_counter() - started) * 1000

    return Prediction(
        instance_id=resolved.instance.id,
        head_name=resolved.instance.name,
        head_type_id=resolved.spec.id,
        task=resolved.spec.task,
        render_hint=resolved.spec.render_hint,
        class_names=resolved.instance.class_names,
        payload=payload,
        grid=features.grid,
        elapsed_ms=elapsed,
    )


def run_inference(
    image: Image.Image,
    backbone_id: str,
    instance_id: str,
    settings: Settings | None = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> Prediction:
    """Run one image through one head and return predictions in source coordinates.

    Delegates to :func:`compose.run_heads` with a single head rather than keeping a
    second copy of the same sequence — one head is simply one pass group. The import is
    function-local because compose builds on this module's per-head step, and a
    module-level import either way would close the cycle.
    """
    from app.ml.inference.compose import run_heads

    result = run_heads(
        image,
        backbone_id,
        [instance_id],
        settings=settings,
        score_threshold=score_threshold,
    )
    return result.predictions[0]
