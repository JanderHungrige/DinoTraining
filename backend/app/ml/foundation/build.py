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
from app.ml.foundation.depth import DepthAnythingModel
from app.ml.foundation.registry import FoundationSpec, get_foundation

logger = logging.getLogger(__name__)


class FoundationUnavailableError(LookupError):
    """No implementation is registered for that id."""


_CACHE: dict[str, DepthAnythingModel] = {}


def build_foundation(
    foundation_id: str, settings: Settings | None = None
) -> DepthAnythingModel:
    """Return the implementation for ``foundation_id``, loading it at most once."""
    spec = get_foundation(foundation_id)
    if spec is None:
        raise FoundationUnavailableError(f"Unknown foundation model: {foundation_id}")

    cached = _CACHE.get(foundation_id)
    if cached is not None:
        return cached

    model = _implementation(spec, settings)
    _CACHE[foundation_id] = model
    return model


def _implementation(
    spec: FoundationSpec, settings: Settings | None
) -> DepthAnythingModel:
    if spec.task == "depth":
        return DepthAnythingModel(spec, settings)
    raise FoundationUnavailableError(f"No implementation for task {spec.task}")


def reset_cache() -> None:
    """Drop loaded models. For tests, and for a settings change that moves the cache dir."""
    _CACHE.clear()


__all__ = ["FoundationUnavailableError", "build_foundation", "reset_cache"]
