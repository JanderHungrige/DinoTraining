"""Frozen DINOv2/v3 feature extraction and the backbone capability descriptor.

Every head in Wave 2 consumes this module's output, so the tensor contract is fixed
here and nowhere else:

    cls      (B, D)          pooled CLS token   → classification heads
    patches  (B, D, Gh, Gw)  channels-first     → detection / segmentation / depth

The backbone is frozen in three ways — ``eval()``, ``requires_grad_(False)`` and a
``no_grad`` forward. ``no_grad`` alone still leaves parameters that an optimizer built
over ``model.parameters()`` would happily update.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.paths import is_installed, resolve_model_dir
from app.ml.errors import ModelNotInstalledError
from app.ml.registry import ModelFamily, ModelSpec, get_model

if TYPE_CHECKING:
    from PIL import Image
    from torch import Tensor

logger = logging.getLogger(__name__)

DEFAULT_BACKBONE = "dinov2-base"


class FeatureShapeError(RuntimeError):
    """The token count did not match the patch grid derived from the input size."""


@dataclass(frozen=True, slots=True)
class BackboneCapabilities:
    """What a backbone can do, read from its config. Head compatibility is checked
    against this — never against a hardcoded assumption about a model family."""

    model_id: str
    family: ModelFamily
    patch_size: int
    embed_dim: int
    num_prefix_tokens: int
    num_layers: int
    image_size: int


@dataclass(frozen=True, slots=True)
class BackboneFeatures:
    """One forward pass. ``patches`` is channels-first so heads are plain ``Conv2d``."""

    cls: Tensor
    patches: Tensor
    grid: tuple[int, int]


@dataclass
class Backbone:
    """A loaded processor + frozen model pair, with its descriptor."""

    capabilities: BackboneCapabilities
    device: str
    processor: Any
    model: Any


_cache: dict[tuple[str, str], Backbone] = {}
_lock = threading.Lock()


def _require_spec(model_id: str) -> ModelSpec:
    spec = get_model(model_id)
    if spec is None:
        raise LookupError(f"Unknown model: {model_id}")
    if spec.kind != "backbone":
        raise ValueError(f"{model_id} is not a backbone")
    return spec


def _require_installed(spec: ModelSpec) -> Path:
    directory = resolve_model_dir(spec.id)
    if not is_installed(directory):
        # No implicit download: this is up to 1.2 GB, and the Admin tab owns that.
        raise ModelNotInstalledError(spec.id)
    return directory


def _read_config(directory: Path, model_id: str) -> dict[str, Any]:
    path = directory / "config.json"
    if not path.is_file():
        raise ValueError(f"{model_id} has no config.json at {path}")
    try:
        parsed = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        # Re-raised with the model named: "Expecting value: line 1" alone tells the
        # user nothing about *which* of their backbones is corrupt.
        raise ValueError(f"{model_id} has an unreadable config.json: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{model_id} has a malformed config.json: expected an object")
    return parsed


def _require_int(config: dict[str, Any], key: str, model_id: str) -> int:
    value = config.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{model_id} config.json is missing an integer {key!r}")
    return value


def read_capabilities(model_id: str) -> BackboneCapabilities:
    """Describe an installed backbone **without loading its weights**.

    Cheapness is the point: `head-catalog-import` must tell the user whether a head
    fits a 1.2 GB backbone, and the Admin tab lists every installed backbone at once.
    Loading weights to answer that would make both unusable.
    """
    spec = _require_spec(model_id)
    directory = _require_installed(spec)
    config = _read_config(directory, model_id)

    # DINOv3 adds register tokens between CLS and the patch tokens. Reading this
    # rather than assuming 1 is what keeps the patch grid aligned — see _split_tokens.
    registers = config.get("num_register_tokens", 0)
    if not isinstance(registers, int):
        registers = 0

    return BackboneCapabilities(
        model_id=spec.id,
        family=spec.family,
        patch_size=_require_int(config, "patch_size", model_id),
        embed_dim=_require_int(config, "hidden_size", model_id),
        num_prefix_tokens=1 + registers,
        num_layers=_require_int(config, "num_hidden_layers", model_id),
        image_size=_require_int(config, "image_size", model_id),
    )


def load_backbone(model_id: str = DEFAULT_BACKBONE) -> Backbone:
    """Load (or reuse) a frozen backbone. Never downloads — that is the Admin tab's job."""
    spec = _require_spec(model_id)
    device = get_settings().resolved_device
    key = (spec.id, device)

    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached

        capabilities = read_capabilities(spec.id)
        directory = _require_installed(spec)

        logger.info("Loading backbone %s on %s", spec.id, device)
        from transformers import AutoImageProcessor, AutoModel

        # transformers ships untyped factory methods; this pair is the library boundary.
        processor = AutoImageProcessor.from_pretrained(str(directory))  # type: ignore[no-untyped-call]
        model = AutoModel.from_pretrained(str(directory)).to(device)
        model.eval()
        # Frozen: only heads train. The trainer builds its optimizer from head
        # parameters, and this is the second line of defence behind that.
        model.requires_grad_(False)

        backbone = Backbone(
            capabilities=capabilities, device=device, processor=processor, model=model
        )
        _cache[key] = backbone
        logger.info("Loaded backbone %s (embed_dim=%d)", spec.id, capabilities.embed_dim)
        return backbone


def _grid_dims(height: int, width: int, patch_size: int) -> tuple[int, int]:
    """Patch-grid dimensions for an input size, rejecting anything indivisible.

    A 225 px input on a patch-14 backbone is not an error in some implementations —
    it quietly drops the remainder. Rejecting it here means a preprocessing bug shows
    up as a message instead of as a model that trains slightly wrong.
    """
    if height % patch_size or width % patch_size:
        raise ValueError(
            f"Input {height}x{width} is not divisible by patch size {patch_size}"
        )
    return height // patch_size, width // patch_size


def _split_tokens(
    hidden: Tensor, num_prefix_tokens: int, grid: tuple[int, int]
) -> tuple[Tensor, Tensor]:
    """Split a ``(B, T, D)`` sequence into the CLS vector and the patch grid.

    ``num_prefix_tokens`` is read from the model config, not assumed to be 1: DINOv3's
    register tokens sit between CLS and the patches, so slicing at a hardcoded 1 shifts
    every patch by the number of registers. That produces correctly *shaped* features
    that are spatially wrong — a head trained on them converges to nothing and the
    cause is invisible. The count check below is what makes that failure loud.
    """
    rows, cols = grid
    expected = rows * cols
    patch_tokens = hidden[:, num_prefix_tokens:, :]
    actual = patch_tokens.shape[1]
    if actual != expected:
        raise FeatureShapeError(
            f"Backbone returned {actual} patch tokens but the {rows}x{cols} grid "
            f"needs {expected}. Check num_prefix_tokens ({num_prefix_tokens}) "
            f"against the model config."
        )

    cls = hidden[:, 0, :]
    batch, _, dim = patch_tokens.shape
    # (B, N, D) → (B, D, Gh, Gw): channels-first so heads are ordinary Conv2d.
    patches = patch_tokens.transpose(1, 2).reshape(batch, dim, rows, cols)
    return cls, patches


def preprocess(backbone: Backbone, images: list[Image.Image]) -> Tensor:
    """Turn PIL images into this backbone's expected ``pixel_values`` tensor."""
    batch = backbone.processor(images=images, return_tensors="pt")
    tensor: Tensor = batch["pixel_values"].to(backbone.device)
    return tensor


def extract(backbone: Backbone, pixel_values: Tensor) -> BackboneFeatures:
    """Run the frozen backbone and return the CLS vector plus the patch grid."""
    import torch

    height, width = int(pixel_values.shape[-2]), int(pixel_values.shape[-1])
    grid = _grid_dims(height, width, backbone.capabilities.patch_size)

    with torch.no_grad():
        outputs = backbone.model(pixel_values=pixel_values.to(backbone.device))

    hidden: Tensor = outputs.last_hidden_state
    cls, patches = _split_tokens(hidden, backbone.capabilities.num_prefix_tokens, grid)
    return BackboneFeatures(cls=cls, patches=patches, grid=grid)


def extract_trainable(backbone: Backbone, pixel_values: Tensor) -> BackboneFeatures:
    """The same forward as :func:`extract`, but **inside the autograd graph** (doc 55).

    A separate function rather than a `grad: bool` flag on `extract`, because every other
    caller in this app wants the `no_grad` guarantee and none of them should be able to lose
    it by passing the wrong argument. Inference, the feature cache and the annotators all
    keep calling `extract` and cannot be affected by anything here.

    Only the *training* path calls this, and only when the user has asked for backbone
    blocks to be unfrozen. With a fully frozen backbone it would allocate a graph that
    nothing backpropagates through — correct, but wasted memory on every image.
    """
    height, width = int(pixel_values.shape[-2]), int(pixel_values.shape[-1])
    grid = _grid_dims(height, width, backbone.capabilities.patch_size)

    outputs = backbone.model(pixel_values=pixel_values.to(backbone.device))
    hidden: Tensor = outputs.last_hidden_state
    cls, patches = _split_tokens(hidden, backbone.capabilities.num_prefix_tokens, grid)
    return BackboneFeatures(cls=cls, patches=patches, grid=grid)


def extract_images(backbone: Backbone, images: list[Image.Image]) -> BackboneFeatures:
    """Convenience for the inference path: PIL images straight to features."""
    return extract(backbone, preprocess(backbone, images))


def clear_cache() -> None:
    """Drop loaded backbones. For tests, and for freeing memory after a device change."""
    with _lock:
        _cache.clear()
