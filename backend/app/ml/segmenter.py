"""SAM 2 inference — boxes in, masks out.

Mirrors ``detector.py``: loaded once per (model_id, device) and cached, because loading
costs seconds and hundreds of megabytes and a per-request load would make the review loop
unusable. Never downloads; that is the Admin tab's job and the user's decision.

Measured against the real checkpoint before this was written, because two things here are
not guessable and both fail silently:

* **One inner list per image, N boxes inside it.** ``input_boxes=[[b1, b2]]`` returns
  ``(2, 1, H, W)`` — one mask per box. Nesting it wrong returns one mask for many boxes.
* **Masks come back on the model's device.** ``.numpy()`` raises on an MPS tensor, which is
  this project's most expensive bug class: every test builds CPU tensors and passes while
  the real runtime 500s. Conversion goes through one ``.detach().cpu().numpy()``.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from PIL import Image

from app.core.config import get_settings
from app.core.paths import is_installed, resolve_model_dir
from app.ml.errors import ModelNotInstalledError
from app.ml.registry import ModelSpec, get_model

logger = logging.getLogger(__name__)

DEFAULT_SEGMENTER = "sam2.1-hiera-small"

#: xyxy, absolute pixels — what SAM 2 expects as a box prompt. Note this is *not* the
#: store's xywh convention; the single conversion lives in `annotators/grounded_sam.py`.
PromptBox = tuple[float, float, float, float]


@dataclass
class Segmenter:
    """A loaded SAM 2 processor + model pair."""

    model_id: str
    device: str
    processor: Any
    model: Any


_cache: dict[tuple[str, str], Segmenter] = {}
_lock = threading.Lock()


def _classes_for(family: str) -> tuple[Any, Any]:
    """The processor/model pair for a segmenter family.

    A table rather than an ``if family == "sam3"``, for the reason the whole annotator
    layer is a registry: the two models differ in how they are *prompted*, which is their
    annotators' business, not the loader's. Loading is the same job either way — resolve a
    directory, refuse to download, move to the device, eval.

    Imported lazily because transformers is slow to import and this is called once per
    process per model.
    """
    if family == "sam2":
        from transformers import Sam2Model, Sam2Processor

        return Sam2Processor, Sam2Model
    if family == "sam3":
        from transformers import Sam3Model, Sam3Processor

        return Sam3Processor, Sam3Model
    raise ValueError(f"No segmenter loader for family {family!r}")


def _require_spec(model_id: str) -> ModelSpec:
    spec = get_model(model_id)
    if spec is None:
        raise LookupError(f"Unknown model: {model_id}")
    if spec.kind != "segmenter":
        raise ValueError(f"{model_id} is not a segmenter")
    return spec


def load_segmenter(model_id: str = DEFAULT_SEGMENTER) -> Segmenter:
    """Load (or reuse) a segmenter. Never downloads."""
    spec = _require_spec(model_id)
    device = get_settings().resolved_device
    key = (spec.id, device)

    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached

        directory = resolve_model_dir(spec.id)
        if not is_installed(directory):
            raise ModelNotInstalledError(spec.id)

        logger.info("Loading %s on %s", spec.id, device)
        processor_cls, model_cls = _classes_for(spec.family)

        # For SAM 2 the checkpoint's config declares `sam2_video` because the repo serves
        # both image and video use; Sam2Model is the image half, and transformers warns
        # about the mismatch on load. Verified against the real weights: masks are exact.
        #
        # `.to()` is the untyped edge here: transformers types it as accepting a
        # PreTrainedModel rather than a device string.
        processor = processor_cls.from_pretrained(str(directory))
        model = model_cls.from_pretrained(str(directory)).to(device)
        model.eval()

        segmenter = Segmenter(
            model_id=spec.id, device=device, processor=processor, model=model
        )
        _cache[key] = segmenter
        logger.info("Loaded %s", spec.id)
        return segmenter


def segment_boxes(
    segmenter: Segmenter, image: Image.Image, boxes: list[PromptBox]
) -> tuple[npt.NDArray[np.bool_], list[float]]:
    """Turn box prompts into masks.

    Returns ``(masks, iou_scores)`` where ``masks`` has shape ``(N, H, W)`` at the image's
    own size and ``iou_scores`` is the model's own confidence per mask.
    """
    import torch

    if not boxes:
        return np.zeros((0, image.height, image.width), dtype=bool), []

    # One inner list per image; every box for that image goes inside it.
    prompt = [[list(box) for box in boxes]]
    inputs = segmenter.processor(
        images=image, input_boxes=prompt, return_tensors="pt"
    ).to(segmenter.device)

    with torch.no_grad():
        outputs = segmenter.model(**inputs, multimask_output=False)

    # (N, 1, H, W) at the original size, one entry per prompt box.
    post = segmenter.processor.post_process_masks(
        outputs.pred_masks, inputs["original_sizes"]
    )[0]

    masks = _to_numpy(post)
    if masks.ndim == 4:
        # Drop the per-box mask-candidate axis: multimask_output=False leaves exactly one.
        masks = masks[:, 0]

    scores = [float(value) for value in _to_numpy(outputs.iou_scores).reshape(-1)]
    return masks.astype(bool), scores


def _to_numpy(tensor: Any) -> npt.NDArray[Any]:
    """The one device→host conversion.

    ``.numpy()`` raises on any tensor that is not a plain CPU leaf, and the model runs on
    MPS here. Reproduced against the real checkpoint: ``TypeError: can't convert mps:0
    device type tensor to numpy``. Routing every conversion through this function is what
    stops that reaching a response.
    """
    array: npt.NDArray[Any] = tensor.detach().cpu().numpy()
    return array


def clear_cache() -> None:
    """Drop loaded models. For tests, and for freeing memory after a device change."""
    with _lock:
        _cache.clear()
