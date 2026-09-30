"""The blocks of a model card (doc 120), each read from the record the app itself uses.

Nothing here is typed by hand: preprocessing is `plan_preprocessing`, the base model is the
catalogue entry, the classes are the stored order. A card that disagreed with the app
would be worse than no card.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from app.datasets.store import DatasetStore
from app.ml.heads.registry import HeadTypeSpec
from app.ml.registry import get_model

logger = logging.getLogger(__name__)

#: How the app reads each head task's raw outputs (docs 09, 16).
OUTPUTS: dict[str, str] = {
    "classification": (
        "logits (B, num_classes) from the CLS token; softmax gives class probabilities, "
        "index i is classes[i]."
    ),
    "detection": (
        "per patch: class logits (B, num_classes, H/p, W/p) and box distances "
        "left/top/right/bottom in patch units (B, 4, H/p, W/p); a box is kept above the "
        "score threshold, overlapping boxes of one class are suppressed, then boxes are "
        "mapped back through the letterbox."
    ),
    "segmentation": (
        "logits (B, num_classes, H/p, W/p), upsampled bilinearly to the input size; argmax "
        "per pixel is the class, then the letterbox padding is cropped and the mask resized "
        "to the picture."
    ),
    "depth": "relative depth (B, 1, H/p, W/p), upsampled to the input size; larger is nearer.",
}


def base_block(model_id: str) -> dict[str, Any]:
    """The catalogue entry and, when installed, its structure (patch size, tokens)."""
    spec = get_model(model_id)
    block: dict[str, Any] = {"id": model_id}
    if spec is not None:
        block.update(
            repo_id=spec.repo_id,
            family=spec.family,
            licence=spec.licence,
            non_commercial=spec.non_commercial,
        )
    if spec is None or spec.kind != "backbone":
        # SAM, RF-DETR, …: not a patch-token backbone; their own processor is the contract.
        return block
    try:
        from app.ml.backbone import read_capabilities

        caps = read_capabilities(model_id)
        block.update(
            patch_size=caps.patch_size,
            embed_dim=caps.embed_dim,
            num_prefix_tokens=caps.num_prefix_tokens,
        )
    except (LookupError, ValueError, OSError) as error:
        # A card for a model whose backbone is not installed here still says what it is.
        logger.info("Model card without backbone structure for %s: %s", model_id, error)
        block["structure_note"] = "backbone not installed here; structure not read"
    return block


def preprocessing_block(model_id: str, spec: HeadTypeSpec) -> dict[str, Any]:
    """Exactly what training and inference do to a picture, from `plan_preprocessing`."""
    try:
        from app.ml.backbone import read_capabilities
        from app.ml.preprocess import plan_preprocessing

        plan = plan_preprocessing(read_capabilities(model_id), spec)
    except (LookupError, ValueError, OSError) as error:
        logger.info("Model card without preprocessing for %s: %s", model_id, error)
        return {"note": "backbone not installed here; preprocessing not read"}
    geometry = (
        "letterbox: scale to fit size x size, pad with 0 (black), centred"
        if plan.geometry == "aspect-preserve"
        else "center-crop: scale the shorter side to size, crop the centre"
    )
    return {
        "geometry": plan.geometry,
        "how": geometry,
        "size": plan.size,
        "resample": "bilinear",
        "scale": "RGB / 255",
        "mean": list(plan.mean),
        "std": list(plan.std),
        "layout": "(B, 3, size, size) float32",
    }


def features_block(consumes: str) -> dict[str, Any]:
    return {
        "from": "last_hidden_state of the base model",
        "prefix_tokens": "the first num_prefix_tokens tokens: CLS (index 0), then registers",
        "patch_grid": "the remaining tokens reshaped to (B, embed_dim, size/p, size/p)",
        "consumes": consumes,
    }


def datasets_block(dataset_ids: tuple[str, ...]) -> list[dict[str, str]]:
    found = []
    for dataset_id in dataset_ids:
        try:
            found.append({"id": dataset_id, "name": DatasetStore().get(dataset_id).name})
        except LookupError:
            found.append({"id": dataset_id, "name": "(deleted)"})
    return found


def recipe_block(dataset_ids: tuple[str, ...], recipe_id: str | None) -> dict[str, str] | None:
    if not recipe_id:
        return None
    from app.prep.recipe import get_recipe

    for dataset_id in dataset_ids:
        recipe = get_recipe(dataset_id, recipe_id)
        if recipe is not None:
            return {"id": recipe.id, "name": recipe.name, "version": str(recipe.version)}
    return {"id": recipe_id, "name": "(not found)"}


def weights_block(paths: list[Path]) -> list[dict[str, Any]]:
    """File name, format and SHA-256 — never the local folder (doc 120, rule 3)."""
    files = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        files.append(
            {"file": path.name, "format": path.suffix.lstrip(".") or "unknown", "sha256": digest}
        )
    return files


def history_block(history: tuple[dict[str, object], ...] | None) -> dict[str, Any]:
    if history is None:
        return {"history": None, "history_note": "not recorded (trained before Wave 15.6)"}
    return {"history": list(history)}


__all__ = [
    "OUTPUTS",
    "base_block",
    "datasets_block",
    "features_block",
    "history_block",
    "preprocessing_block",
    "recipe_block",
    "weights_block",
]
