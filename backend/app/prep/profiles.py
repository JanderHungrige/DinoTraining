"""What each trainable model does to an image before it sees it (docs 81, 85).

The audit judges object sizes *at the model's input*, and input planning (doc 85) decides
whether to tile. Both need the same facts, so they live here once:

* the input size and how an image is fitted to it (letterbox to a square, or resize by the
  shortest edge);
* the smallest object the model can still resolve at that input, which is about two
  feature-map cells: an object smaller than one cell has no position of its own to be found
  at.

Sizes are **read from the installed model's own `preprocessor_config.json`** when it is
there, so a model whose processor changes does not silently disagree with this table. The
defaults below are the values those files held on 2026-09-29, and apply when the model is
not installed yet.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, replace
from pathlib import Path

from app.core.config import Settings
from app.core.paths import model_cache_root

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ModelProfile:
    id: str
    label: str
    #: "detection", "segmentation" or "classification".
    task: str
    #: "boxes", "masks" or "labels": what the training target is made from.
    annotation_kind: str
    #: "letterbox": scale the longest edge to `input_size`, pad to a square.
    #: "shortest-edge": scale the shortest edge to `input_size`, capped at `max_long_edge`.
    #: "stretch": resize to an `input_size` square, aspect ratio not kept.
    fit: str
    input_size: int
    #: One feature-map cell, in input pixels (the patch size or the detector's finest stride).
    cell_px: int
    max_long_edge: int | None = None
    #: The catalogue model whose processor config is authoritative, when there is one.
    model_id: str | None = None

    @property
    def min_visible_px(self) -> int:
        """About two cells: below this an object has no location of its own in the features."""
        return 2 * self.cell_px

    def scale_for(self, width: int, height: int) -> float:
        """Source pixels → input pixels, for an image of this size.

        For a stretch x and y scale apart, and this is their geometric mean: exact for an
        object's size measured as the square root of its area, which is how it is measured.
        """
        if self.fit == "stretch":
            return self.input_size / math.sqrt(max(1, width) * max(1, height))
        if self.fit == "shortest-edge":
            scale = self.input_size / max(1, min(width, height))
            if self.max_long_edge is not None:
                scale = min(scale, self.max_long_edge / max(1, max(width, height)))
            return scale
        return self.input_size / max(1, max(width, height))


PROFILES: tuple[ModelProfile, ...] = (
    ModelProfile(
        "head-detection-dinov2",
        "Detection head on DINOv2",
        "detection",
        "boxes",
        "letterbox",
        448,
        14,
        model_id=None,
    ),
    ModelProfile(
        "head-detection-dinov3",
        "Detection head on DINOv3",
        "detection",
        "boxes",
        "letterbox",
        448,
        16,
        model_id=None,
    ),
    ModelProfile(
        "head-segmentation-dinov2",
        "Segmentation head on DINOv2",
        "segmentation",
        "masks",
        "letterbox",
        448,
        14,
    ),
    ModelProfile(
        "head-classification-dinov2",
        "Classification head on DINOv2",
        "classification",
        "labels",
        "letterbox",
        224,
        14,
    ),
    ModelProfile(
        "rf-detr-nano",
        "Fine-tune RF-DETR (nano)",
        "detection",
        "boxes",
        "stretch",
        384,
        8,
        model_id="rf-detr-nano",
    ),
    ModelProfile(
        "sam2.1-hiera-small",
        "Fine-tune SAM 2.1 (small)",
        "segmentation",
        "masks",
        "stretch",
        1024,
        16,
        model_id="sam2.1-hiera-small",
    ),
)

_BY_ID = {profile.id: profile for profile in PROFILES}


def _read_processor(model_dir: Path) -> dict[str, object] | None:
    path = model_dir / "preprocessor_config.json"
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        logger.info("Unreadable processor config %s: %s", path, error)
        return None
    return loaded if isinstance(loaded, dict) else None


def _from_processor(profile: ModelProfile, config: dict[str, object]) -> ModelProfile:
    size = config.get("size")
    if not isinstance(size, dict):
        return profile
    if isinstance(size.get("height"), int) and isinstance(size.get("width"), int):
        # {height, width} is an exact size: the processor stretches, it does not pad
        # (transformers: "Do NOT keep the aspect ratio"). Read as a letterbox until
        # 2026-09-29, which misjudged every object in a wide frame.
        return replace(profile, fit="stretch", input_size=max(size["height"], size["width"]))
    if isinstance(size.get("shortest_edge"), int):
        long_edge = size.get("longest_edge")
        return replace(
            profile,
            fit="shortest-edge",
            input_size=size["shortest_edge"],
            max_long_edge=long_edge if isinstance(long_edge, int) else None,
        )
    return profile


def get_profile(profile_id: str, settings: Settings | None = None) -> ModelProfile:
    """A profile, with its input size read from the installed model when there is one."""
    profile = _BY_ID.get(profile_id)
    if profile is None:
        raise KeyError(profile_id)
    if profile.model_id is None:
        return profile
    config = _read_processor(model_cache_root(settings) / profile.model_id)
    return _from_processor(profile, config) if config else profile


def list_profiles(settings: Settings | None = None) -> list[ModelProfile]:
    return [get_profile(profile.id, settings) for profile in PROFILES]


__all__ = ["PROFILES", "ModelProfile", "get_profile", "list_profiles"]
