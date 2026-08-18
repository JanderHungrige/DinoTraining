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

import torch
from PIL import Image

from app.core.config import Settings, get_settings
from app.ml.backbone import Backbone, extract, load_backbone, read_capabilities
from app.ml.heads.builders import build_head
from app.ml.heads.decode import decode_for
from app.ml.heads.instances import HeadInstance
from app.ml.heads.modules import upsample_logits
from app.ml.heads.registry import HeadTypeSpec, get_head_type
from app.ml.heads.store import HeadInstanceStore
from app.ml.inference.geometry import invert_boxes, invert_map
from app.ml.inference.results import Prediction
from app.ml.preprocess import GeometryTransform, plan_preprocessing, prepare_images

logger = logging.getLogger(__name__)

#: Detections kept for display. The decoder already ranks by score.
MAX_DISPLAY_BOXES = 50

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


def run_inference(
    image: Image.Image,
    backbone_id: str,
    instance_id: str,
    settings: Settings | None = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> Prediction:
    """Run one image through one head and return predictions in source coordinates."""
    settings = settings or get_settings()
    started = time.perf_counter()

    instance = _require_instance(instance_id, settings)
    if instance.backbone_id != backbone_id:
        raise BackboneMismatchError(
            f"{instance.name} was registered for {instance.backbone_id}, "
            f"but {backbone_id} was requested. Select {instance.backbone_id} to run it."
        )

    spec = _require_spec(instance)
    capabilities = read_capabilities(backbone_id)

    # Derived from the (backbone, head) pair — never passed in. If a caller could
    # supply geometry, a head would behave one way in the trainer and another here.
    plan = plan_preprocessing(capabilities, spec)
    pixel_values, transforms = prepare_images(plan, [image])

    backbone = load_backbone(backbone_id)
    head = load_head(instance, backbone, settings)

    with torch.no_grad():
        features = extract(backbone, pixel_values)
        outputs = head(features)

    decoded = decode_for(spec)(outputs, capabilities.patch_size)
    payload = _build_payload(spec, decoded, transforms[0], plan.size, score_threshold)

    elapsed = (time.perf_counter() - started) * 1000
    logger.info("Inference %s on %s in %.0f ms", instance.id, backbone_id, elapsed)

    return Prediction(
        instance_id=instance.id,
        head_name=instance.name,
        head_type_id=spec.id,
        task=spec.task,
        render_hint=spec.render_hint,
        class_names=instance.class_names,
        payload=payload,
        grid=features.grid,
        elapsed_ms=elapsed,
    )


def _build_payload(
    spec: HeadTypeSpec,
    decoded: dict[str, torch.Tensor],
    transform: GeometryTransform,
    frame_size: int,
    score_threshold: float,
) -> dict[str, object]:
    """Shape the decoder's output for the render hint, in source coordinates.

    Keyed off ``render_hint`` rather than task: two head types can share a task and a
    renderer, and the hint is what feature 20 dispatches on.
    """
    if spec.render_hint == "labels":
        return _labels_payload(decoded)
    if spec.render_hint == "boxes":
        return _boxes_payload(decoded, transform, score_threshold)
    if spec.render_hint == "masks":
        return _masks_payload(decoded, transform, frame_size)
    return _depth_payload(decoded, transform, frame_size)


def _labels_payload(decoded: dict[str, torch.Tensor]) -> dict[str, object]:
    logits = decoded["logits"][0]
    scores = torch.softmax(logits.float(), dim=-1)
    return {"scores": [float(value) for value in scores]}


def _boxes_payload(
    decoded: dict[str, torch.Tensor], transform: GeometryTransform, threshold: float
) -> dict[str, object]:
    scores = decoded["scores"]
    keep = scores >= threshold
    if not bool(keep.any()):
        return {"boxes": [], "scores": [], "classes": []}

    kept_boxes = decoded["boxes"][keep][:MAX_DISPLAY_BOXES]
    kept_scores = scores[keep][:MAX_DISPLAY_BOXES]
    kept_classes = decoded["classes"][keep][:MAX_DISPLAY_BOXES]

    frame_boxes = [tuple(float(v) for v in box) for box in kept_boxes]
    source_boxes = invert_boxes(transform, frame_boxes)  # type: ignore[arg-type]

    # A box predicted entirely inside the letterbox padding inverts to zero area: it
    # describes pixels the user's image does not have. Dropped here rather than left
    # for the renderer to filter — and dropped from all three arrays together, because
    # they are read positionally and a partial drop misaligns every later score.
    survivors = [
        (box, float(score), int(cls))
        for box, score, cls in zip(source_boxes, kept_scores, kept_classes, strict=True)
        if box[2] > 0.0 and box[3] > 0.0
    ]

    return {
        "boxes": [list(box) for box, _, _ in survivors],
        "scores": [score for _, score, _ in survivors],
        "classes": [cls for _, _, cls in survivors],
    }


def _masks_payload(
    decoded: dict[str, torch.Tensor], transform: GeometryTransform, frame_size: int
) -> dict[str, object]:
    # Patch resolution -> frame resolution -> source resolution. The head has no idea
    # what size to upsample to, which is why upsample_logits takes it explicitly.
    logits = decoded["logits"]
    at_frame = upsample_logits(logits.float(), (frame_size, frame_size))
    classes = at_frame[0].argmax(dim=0).float()
    # nearest: bilinear on a label map averages class ids into classes nobody predicted.
    at_source = invert_map(transform, classes, mode="nearest").round().to(torch.int64)

    return {
        "mask": at_source.tolist(),
        "present_classes": sorted({int(v) for v in at_source.flatten().tolist()}),
        "height": int(at_source.shape[0]),
        "width": int(at_source.shape[1]),
    }


def _depth_payload(
    decoded: dict[str, torch.Tensor], transform: GeometryTransform, frame_size: int
) -> dict[str, object]:
    depth = decoded["depth"].float()
    at_frame = torch.nn.functional.interpolate(
        depth, size=(frame_size, frame_size), mode="bilinear", align_corners=False
    )
    # bilinear here: depth is continuous, so interpolation is meaningful — the opposite
    # of the label-map case above.
    at_source = invert_map(transform, at_frame[0, 0], mode="bilinear")

    return {
        "depth": at_source.tolist(),
        "min": float(at_source.min()),
        "max": float(at_source.max()),
        "height": int(at_source.shape[0]),
        "width": int(at_source.shape[1]),
    }
