"""Task-aware preprocessing, with targets that move exactly as the image did.

Doc 07 found that the stock DINOv2 processor centre-crops to 224. That is correct for
classification and destructive for dense tasks: annotations outside the crop vanish
while training loss still looks perfectly healthy. So geometry is chosen from the head
spec, and every geometric operation returns a :class:`GeometryTransform` that targets
are passed through — a target transform is not a *re-derivation* of what happened to
the image, it is the same numbers.

Per CLAUDE.md the plan is derived from backbone + head. It is never configured by a
caller and never asked of the user.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import torch
from PIL import Image
from torch import Tensor

from app.core.paths import resolve_model_dir
from app.ml.backbone import BackboneCapabilities
from app.ml.heads.registry import HeadTypeSpec, PreprocessGeometry

logger = logging.getLogger(__name__)

Box = tuple[float, float, float, float]

#: DINOv2 and DINOv3 both normalise with ImageNet statistics. Used only when a model
#: ships no preprocessor_config.json — hardcoding outright would break silently for a
#: future backbone trained with different statistics.
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

#: Classification is a whole-image label, so a 16x16 grid is plenty.
CLASSIFICATION_SIZE = 224
#: Dense tasks are bounded by grid resolution — a 16x16 grid cannot express small objects.
DENSE_SIZE = 448

#: Mask value meaning "not annotated". Padded letterbox regions get this rather than
#: class 0, which would teach the model that padding is background.
DEFAULT_IGNORE_INDEX = 255


@dataclass(frozen=True, slots=True)
class PreprocessPlan:
    """How to prepare an image for one (backbone, head) pair. Derived, never configured."""

    size: int
    geometry: PreprocessGeometry
    patch_size: int
    mean: tuple[float, float, float]
    std: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class GeometryTransform:
    """Exactly what happened to an image, so targets can be put through the same thing."""

    scale: float
    pad_x: float
    pad_y: float
    out_w: int
    out_h: int
    source_size: tuple[int, int]


def _round_to_patch(size: int, patch_size: int) -> int:
    """Nearest multiple of the patch size, at least one patch.

    Doc 07 rejects inputs that do not divide evenly, so a non-conforming size must be
    impossible to produce here rather than blowing up at the forward pass.
    """
    multiple = max(1, round(size / patch_size))
    return multiple * patch_size


def _read_normalisation(model_id: str) -> tuple[
    tuple[float, float, float], tuple[float, float, float]
]:
    """Mean/std from the model's own preprocessor_config.json, ImageNet as fallback."""
    path = resolve_model_dir(model_id) / "preprocessor_config.json"
    if not path.is_file():
        return IMAGENET_MEAN, IMAGENET_STD
    try:
        config = json.loads(path.read_text())
        mean = tuple(float(v) for v in config["image_mean"])
        std = tuple(float(v) for v in config["image_std"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        # Not fatal: the ImageNet defaults are right for every backbone shipped today.
        # Logged because a silently wrong normalisation degrades accuracy invisibly.
        logger.warning("Falling back to ImageNet stats for %s: %s", model_id, exc)
        return IMAGENET_MEAN, IMAGENET_STD
    if len(mean) != 3 or len(std) != 3:
        logger.warning("Ignoring malformed normalisation stats for %s", model_id)
        return IMAGENET_MEAN, IMAGENET_STD
    return (mean[0], mean[1], mean[2]), (std[0], std[1], std[2])


def plan_preprocessing(
    capabilities: BackboneCapabilities, spec: HeadTypeSpec
) -> PreprocessPlan:
    """Derive the plan from the backbone and the head. The only sanctioned entry point."""
    target = CLASSIFICATION_SIZE if spec.geometry == "center-crop" else DENSE_SIZE
    mean, std = _read_normalisation(capabilities.model_id)
    return PreprocessPlan(
        size=_round_to_patch(target, capabilities.patch_size),
        geometry=spec.geometry,
        patch_size=capabilities.patch_size,
        mean=mean,
        std=std,
    )


def _letterbox(plan: PreprocessPlan, image: Image.Image) -> tuple[Image.Image, GeometryTransform]:
    """Scale to fit and pad the remainder. Lossless: nothing leaves the frame."""
    source_w, source_h = image.size
    scale = min(plan.size / source_w, plan.size / source_h)
    new_w, new_h = max(1, round(source_w * scale)), max(1, round(source_h * scale))

    resized = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
    canvas = Image.new(image.mode, (plan.size, plan.size), 0)
    pad_x, pad_y = (plan.size - new_w) // 2, (plan.size - new_h) // 2
    canvas.paste(resized, (pad_x, pad_y))

    return canvas, GeometryTransform(
        scale=scale,
        pad_x=float(pad_x),
        pad_y=float(pad_y),
        out_w=plan.size,
        out_h=plan.size,
        source_size=(source_w, source_h),
    )


def _center_crop(plan: PreprocessPlan, image: Image.Image) -> tuple[Image.Image, GeometryTransform]:
    """Resize the shortest edge, then crop the centre. Can discard content — which is
    why only classification uses it, where the label describes the whole image."""
    source_w, source_h = image.size
    scale = plan.size / min(source_w, source_h)
    new_w, new_h = max(1, round(source_w * scale)), max(1, round(source_h * scale))

    resized = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
    left, top = (new_w - plan.size) // 2, (new_h - plan.size) // 2
    cropped = resized.crop((left, top, left + plan.size, top + plan.size))

    # Negative padding: a crop shifts content the opposite way to a pad, so targets go
    # through the identical formula and no caller has to special-case the geometry.
    return cropped, GeometryTransform(
        scale=scale,
        pad_x=float(-left),
        pad_y=float(-top),
        out_w=plan.size,
        out_h=plan.size,
        source_size=(source_w, source_h),
    )


def apply_geometry(
    plan: PreprocessPlan, image: Image.Image
) -> tuple[Image.Image, GeometryTransform]:
    """Resize an image per the plan, returning the transform targets must follow."""
    if plan.geometry == "aspect-preserve":
        return _letterbox(plan, image)
    return _center_crop(plan, image)


def transform_boxes(
    transform: GeometryTransform, boxes: list[Box]
) -> tuple[list[Box], list[int]]:
    """Move xywh boxes into the transformed frame, clipping to the canvas.

    The inverse — predictions in the frame back onto the source image — is
    ``app.ml.inference.geometry.invert_boxes``. Edit one, look at the other.

    Returns the surviving boxes **and their original indices**. The indices are not
    bookkeeping: dropping a box without dropping its label silently misaligns every
    remaining label in that sample, which is unrecoverable downstream.
    """
    kept: list[Box] = []
    keep_indices: list[int] = []

    for index, (x, y, w, h) in enumerate(boxes):
        x_min = x * transform.scale + transform.pad_x
        y_min = y * transform.scale + transform.pad_y
        x_max = x_min + w * transform.scale
        y_max = y_min + h * transform.scale

        x_min, y_min = max(x_min, 0.0), max(y_min, 0.0)
        x_max = min(x_max, float(transform.out_w))
        y_max = min(y_max, float(transform.out_h))

        width, height = x_max - x_min, y_max - y_min
        if width <= 0 or height <= 0:
            # Dropped, not clamped: a zero-area box fails the store's CHECK constraint
            # and contributes nothing but noise to a loss.
            continue

        kept.append((x_min, y_min, width, height))
        keep_indices.append(index)

    return kept, keep_indices


def transform_mask(
    plan: PreprocessPlan, mask: Image.Image, ignore_index: int = DEFAULT_IGNORE_INDEX
) -> Image.Image:
    """Resize a label mask with nearest-neighbour, padding with ``ignore_index``.

    Nearest-neighbour is mandatory: bilinear resampling of a label map averages class
    ids and invents classes that were never annotated. Padding is ``ignore_index``
    rather than 0, so the loss skips it instead of learning that padding is background.
    """
    source_w, source_h = mask.size

    if plan.geometry == "aspect-preserve":
        scale = min(plan.size / source_w, plan.size / source_h)
        new_w, new_h = max(1, round(source_w * scale)), max(1, round(source_h * scale))
        resized = mask.resize((new_w, new_h), Image.Resampling.NEAREST)
        canvas = Image.new(mask.mode, (plan.size, plan.size), ignore_index)
        canvas.paste(resized, ((plan.size - new_w) // 2, (plan.size - new_h) // 2))
        return canvas

    scale = plan.size / min(source_w, source_h)
    new_w, new_h = max(1, round(source_w * scale)), max(1, round(source_h * scale))
    resized = mask.resize((new_w, new_h), Image.Resampling.NEAREST)
    left, top = (new_w - plan.size) // 2, (new_h - plan.size) // 2
    return resized.crop((left, top, left + plan.size, top + plan.size))


def to_pixel_values(plan: PreprocessPlan, images: list[Image.Image]) -> Tensor:
    """Stack already-resized images into a normalised ``(B, 3, H, W)`` float tensor."""
    import numpy as np

    tensors: list[Tensor] = []
    for image in images:
        rgb = image if image.mode == "RGB" else image.convert("RGB")
        array = np.asarray(rgb, dtype=np.float32) / 255.0
        tensors.append(torch.from_numpy(array).permute(2, 0, 1))

    batch = torch.stack(tensors)
    mean = torch.tensor(plan.mean, dtype=torch.float32).view(1, 3, 1, 1)
    std = torch.tensor(plan.std, dtype=torch.float32).view(1, 3, 1, 1)
    return (batch - mean) / std


def prepare_images(
    plan: PreprocessPlan, images: list[Image.Image]
) -> tuple[Tensor, list[GeometryTransform]]:
    """Full path for a batch: geometry then normalisation, transforms returned."""
    resized: list[Image.Image] = []
    transforms: list[GeometryTransform] = []
    for image in images:
        out, transform = apply_geometry(plan, image)
        resized.append(out)
        transforms.append(transform)
    return to_pixel_values(plan, resized), transforms
