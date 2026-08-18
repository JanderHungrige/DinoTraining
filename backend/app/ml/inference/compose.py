"""Many heads, one backbone pass per framing.

The engine owns *features from an image*; this module owns *many heads from one set of
features*. That split exists because the second job has exactly one interesting decision
in it — which heads can share a pass — and it is easy to get wrong in a way that still
returns correct-looking answers, just N times slower.

The pass key is ``(backbone_id, geometry, size)`` and nothing else. ``consumes`` is not
part of it: ``cls`` and ``patches`` come out of the same ``BackboneFeatures``. What is
impossible is synthesising one pass from another — the CLS token is attention over every
patch in *its* pass, and a 14 px patch at 448 covers half the extent it does at 224. The
reasoning is in doc 18.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import torch
from PIL import Image

from app.core.config import Settings, get_settings
from app.ml.backbone import extract, load_backbone, read_capabilities
from app.ml.heads.registry import PreprocessGeometry
from app.ml.inference.engine import (
    DEFAULT_SCORE_THRESHOLD,
    ResolvedHead,
    predict_from_features,
    resolve_head,
)
from app.ml.inference.results import Prediction
from app.ml.preprocess import PreprocessPlan, plan_preprocessing, prepare_images

logger = logging.getLogger(__name__)

#: What makes two heads able to share a forward pass.
PassKey = tuple[str, PreprocessGeometry, int]


def pass_key(backbone_id: str, plan: PreprocessPlan) -> PassKey:
    """The identity of a backbone pass.

    ``geometry`` and ``size`` are the only plan fields a head can vary — the rest come
    from the backbone — so this is less a chosen key than an observed one.
    """
    return (backbone_id, plan.geometry, plan.size)


@dataclass(frozen=True, slots=True)
class ComposedResult:
    """Predictions in the caller's order, plus what they cost."""

    predictions: tuple[Prediction, ...]
    #: Backbone forward passes actually run. The only external proof grouping happened.
    passes: int
    #: Wall clock for everything. Per-head timings sum to less; the gap is the sharing.
    elapsed_ms: float


def run_heads(
    image: Image.Image,
    backbone_id: str,
    instance_ids: list[str],
    settings: Settings | None = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> ComposedResult:
    """Run several heads over one image, sharing a backbone pass wherever possible."""
    settings = settings or get_settings()
    started = time.perf_counter()

    # First occurrence wins: two identical predictions carry no information, and the
    # request is still coherent without them.
    unique = list(dict.fromkeys(instance_ids))
    if not unique:
        raise ValueError("Select at least one head to run.")

    # Everything is resolved before any compute. Resolving lazily would make the user
    # wait for a 448 pass to find out they named a head that does not exist.
    resolved = [resolve_head(instance_id, backbone_id, settings) for instance_id in unique]

    capabilities = read_capabilities(backbone_id)
    # Derived from the (backbone, head) pair — never passed in, exactly as in the
    # single-head path. A caller-supplied geometry would make a head behave one way in
    # the trainer and another here.
    plans = [plan_preprocessing(capabilities, head.spec) for head in resolved]

    groups: dict[PassKey, list[int]] = {}
    for index, plan in enumerate(plans):
        groups.setdefault(pass_key(backbone_id, plan), []).append(index)

    backbone = load_backbone(backbone_id)
    # Indexed by request position, not appended to: grouping reorders the work and must
    # not reorder the answers, or a comparison view mislabels every column.
    predictions: list[Prediction | None] = [None] * len(resolved)

    for key, members in groups.items():
        plan = plans[members[0]]
        pixel_values, transforms = prepare_images(plan, [image])
        with torch.no_grad():
            features = extract(backbone, pixel_values)

        for index in members:
            predictions[index] = predict_from_features(
                resolved[index],
                features,
                transforms[0],
                plan,
                backbone,
                settings,
                score_threshold,
            )
        logger.debug("Pass %s served %d head(s)", key, len(members))

    elapsed = (time.perf_counter() - started) * 1000
    logger.info(
        "Composed %d head(s) over %d pass(es) on %s in %.0f ms",
        len(resolved),
        len(groups),
        backbone_id,
        elapsed,
    )

    # Every slot is filled: the groups partition the same index range.
    return ComposedResult(
        predictions=tuple(p for p in predictions if p is not None),
        passes=len(groups),
        elapsed_ms=elapsed,
    )


__all__ = ["ComposedResult", "PassKey", "ResolvedHead", "pass_key", "run_heads"]
