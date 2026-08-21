"""The only place a foundation-model id maps to an implementation.

Mirrors `app/ml/annotators/build.py` deliberately. A `if foundation_id == "…"` anywhere
else is a defect, exactly as `task ===` is in `components/overlays/` — that rule is what
keeps adding the next foundation model a catalogue entry plus one case here.

Instances are cached per id because loading weights costs seconds and the viewer runs the
same model over every image in a folder.
"""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.paths import PathConfinementError
from app.ml.foundation.concept import ConceptSegmenter
from app.ml.foundation.depth import DepthAnythingModel
from app.ml.foundation.detect import RfDetrModel
from app.ml.foundation.registry import FoundationSpec, get_foundation

#: Every foundation implementation. A union rather than a Protocol: they share `predict`
#: but not its signature — the detector takes a score threshold and the depth model has
#: nothing to threshold — and a Protocol wide enough to cover both would describe neither.
FoundationImplementation = ConceptSegmenter | DepthAnythingModel | RfDetrModel

logger = logging.getLogger(__name__)


class FoundationUnavailableError(LookupError):
    """No implementation is registered for that id."""


_CACHE: dict[str, FoundationImplementation] = {}


def build_foundation(
    foundation_id: str, settings: Settings | None = None, *, fresh: bool = False
) -> FoundationImplementation:
    """Return the implementation for ``foundation_id``, loading it at most once.

    An id is either a catalogue entry or a **fine-tuned instance** (doc 44). Both resolve
    here, so every caller — the viewer, the Studio, the Generator — treats a model the user
    trained exactly like one they downloaded.

    ``fresh`` returns an instance that is neither taken from nor put into the cache. Fine-
    tuning needs it: it retargets the classifier and rewrites the weights, and doing that to
    the shared instance turns every later `rf-detr-nano` request into the fine-tuned model.
    That shipped once — the base detector answered with the fine-tune's classes and its
    exact scores, which reads as a plausible result rather than a bug.
    """
    spec = get_foundation(foundation_id) or _trained_spec(foundation_id, settings)
    if spec is None:
        raise FoundationUnavailableError(f"Unknown foundation model: {foundation_id}")

    if fresh:
        return _implementation(spec, settings)

    cached = _CACHE.get(foundation_id)
    if cached is not None:
        return cached

    model = _implementation(spec, settings)
    _CACHE[foundation_id] = model
    return model


def _trained_spec(
    foundation_id: str, settings: Settings | None
) -> FoundationSpec | None:
    """A fine-tuned model as a spec, or None if no instance has that id."""
    from app.ml.foundation.instances import FoundationInstanceStore

    store = FoundationInstanceStore(settings)
    try:
        instance = store.get(foundation_id)
    except PathConfinementError:
        # A traversal attempt is simply not an instance id. Reported as "unknown model"
        # by the caller, which is both true and the same answer any other bad id gets —
        # a distinct error here would confirm that the path shape was interesting.
        return None
    if instance is None:
        return None
    return FoundationSpec(
        id=instance.id,
        model_id=instance.base_model_id,
        title=instance.name,
        description=instance.summary,
        task="detection",
        render_hint="boxes",
        weights_dir=store.directory(instance.id),
        class_names=instance.class_names,
    )


def _implementation(
    spec: FoundationSpec, settings: Settings | None
) -> FoundationImplementation:
    # Checked before `task`, because a concept-prompted pipeline is not one checkpoint
    # and its id would otherwise fall through to "no implementation".
    if spec.annotator_id is not None:
        return ConceptSegmenter(spec, settings)
    if spec.task == "depth":
        return DepthAnythingModel(spec, settings)
    if spec.task == "detection":
        return RfDetrModel(spec, settings)
    raise FoundationUnavailableError(f"No implementation for task {spec.task}")


def reset_cache() -> None:
    """Drop loaded models. For tests, and for a settings change that moves the cache dir."""
    _CACHE.clear()


__all__ = [
    "FoundationImplementation",
    "FoundationUnavailableError",
    "build_foundation",
    "reset_cache",
]
