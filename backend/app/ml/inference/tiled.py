"""Running a head over the grid it was trained on (doc 62).

Doc 49 tiles images on the way *in* and nothing tiled on the way out, so a head trained on
616 px tiles found nothing on a full 2464 px frame — and said nothing about why, because the
run succeeded, the pass count was right and the answer was an empty list.

The arithmetic is doc 49's, unchanged: OSDaR23's median annotated object is 10.7 px in a
2464 px frame, which at a 448 px input arrives as **1.9 px** — below the 7 px stride the
detector predicts on. It is not a hard example, it is not in the tensor. A 4x3 grid makes
the same object 7.8 px at input, which is representable. A head that learned to find the
second will not find the first.

**`plan_tiles` is called, never reimplemented.** `tiling_images.py` already records the
reason: "the two must agree or the result is silently wrong". An inference grid differing
from the training grid by a rounding rule puts every box slightly off and nothing raises.

**One backbone pass for all tiles.** `prepare_images` takes a list and `BackboneFeatures` is
batched throughout, so the expensive part is paid once. Decoding stays per tile, because
`boxes_payload` masks over a flat score vector and a batched one would flatten across
images.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import torch
from PIL import Image
from torchvision.ops import batched_nms

from app.core.config import Settings, get_settings
from app.datasets.tiling import DEFAULT_OVERLAP, Tile, plan_tiles
from app.ml.backbone import BackboneFeatures, extract, load_backbone, read_capabilities
from app.ml.heads.decode import NMS_IOU_THRESHOLD
from app.ml.inference.engine import (
    DEFAULT_SCORE_THRESHOLD,
    ResolvedHead,
    predict_from_features,
    resolve_head,
)
from app.ml.inference.payloads import MAX_DISPLAY_BOXES, source_boxes_payload
from app.ml.inference.results import Prediction
from app.ml.preprocess import plan_preprocessing, prepare_images

logger = logging.getLogger(__name__)

#: The one render hint tiling has an answer for. A tiled depth map would show its seams and
#: a tiled label map is a real feature but a different one — see doc 62's rule 1.
TILEABLE_HINT = "boxes"


@dataclass(frozen=True, slots=True)
class TileGrid:
    """How to cut the frame. A 1x1 grid is the whole frame, and is not an error."""

    columns: int
    rows: int
    overlap: float = DEFAULT_OVERLAP

    @property
    def is_whole_frame(self) -> bool:
        return self.columns == 1 and self.rows == 1


def run_tiled(
    image: Image.Image,
    backbone_id: str,
    instance_ids: list[str],
    grid: TileGrid,
    settings: Settings | None = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> tuple[tuple[Prediction, ...], int, float]:
    """Run heads over a grid and return frame-coordinate predictions.

    Returns `(predictions, passes, elapsed_ms)` rather than a `ComposedResult` so
    `compose.run_heads` stays the one place that assembles one — this is a different way to
    *get* predictions, not a second definition of what they are.
    """
    settings = settings or get_settings()
    started = time.perf_counter()

    unique = list(dict.fromkeys(instance_ids))
    if not unique:
        raise ValueError("Select at least one head to run.")
    resolved = [resolve_head(instance_id, backbone_id, settings) for instance_id in unique]

    tiles = plan_tiles(image.width, image.height, grid.columns, grid.rows, grid.overlap)
    crops = [image.crop((t.x, t.y, t.x + t.width, t.y + t.height)) for t in tiles]

    capabilities = read_capabilities(backbone_id)
    backbone = load_backbone(backbone_id)
    predictions: list[Prediction] = []
    passes = 0

    for head in resolved:
        plan = plan_preprocessing(capabilities, head.spec)
        pixel_values, transforms = prepare_images(plan, crops)
        with torch.no_grad():
            features = extract(backbone, pixel_values)
        passes += 1

        per_tile = [
            predict_from_features(
                head,
                _slice(features, index),
                transforms[index],
                plan,
                backbone,
                settings,
                score_threshold,
            )
            for index in range(len(tiles))
        ]
        predictions.append(merge_tiles(per_tile, tiles, head))

    elapsed = (time.perf_counter() - started) * 1000
    logger.info(
        "Tiled %dx%d over %dx%d: %d tile(s), %d head(s) in %.0f ms",
        grid.columns,
        grid.rows,
        image.width,
        image.height,
        len(tiles),
        len(resolved),
        elapsed,
    )
    return tuple(predictions), passes, elapsed


def _slice(features: BackboneFeatures, index: int) -> BackboneFeatures:
    """One tile's features out of a batched pass.

    A view, not a copy: `predict_from_features` only reads them, and copying twelve
    patch grids would undo the point of batching the pass.
    """
    return BackboneFeatures(
        cls=features.cls[index : index + 1],
        patches=features.patches[index : index + 1],
        grid=features.grid,
    )


def merge_tiles(
    per_tile: list[Prediction], tiles: list[Tile], head: ResolvedHead
) -> Prediction:
    """Offset every tile's boxes into frame coordinates and suppress the duplicates.

    **Overlap is why a merge is needed and why it is cheap.** The grid overlaps so an object
    sitting on a seam is whole in *some* tile; the cost is that it is then found twice, and
    NMS is exactly what that costs. Class-aware, with the same threshold doc 43 uses within
    a tile — a rail beside a signal legitimately overlaps, and suppressing across classes
    would delete the rarer one.

    A head that does not predict boxes comes back as its first tile untouched: the request
    was coherent, tiling simply has nothing to do with a label or a depth map.
    """
    if head.spec.render_hint != TILEABLE_HINT:
        return per_tile[0]

    boxes: list[tuple[float, float, float, float]] = []
    scores: list[float] = []
    classes: list[int] = []

    for prediction, tile in zip(per_tile, tiles, strict=True):
        # The payload arrays rather than `detections()`: that helper resolves the class to
        # its *name*, and NMS and `source_boxes_payload` both want the index. The three are
        # aligned by construction — `boxes_payload` drops a zero-area box from all three at
        # once — so a length mismatch means the payload came from something else.
        raw = _payload_arrays(prediction)
        if raw is None:
            continue
        for (x, y, w, h), score, class_index in raw:
            # The one line that makes a tile's answer a frame's answer.
            boxes.append((x + tile.x, y + tile.y, w, h))
            scores.append(score)
            classes.append(class_index)

    kept = _suppress(boxes, scores, classes)
    payload = source_boxes_payload(
        [boxes[i] for i in kept],
        [scores[i] for i in kept],
        [classes[i] for i in kept],
    )

    first = per_tile[0]
    return Prediction(
        instance_id=first.instance_id,
        head_name=first.head_name,
        head_type_id=first.head_type_id,
        task=first.task,
        render_hint=first.render_hint,
        class_names=first.class_names,
        payload=payload,
        grid=first.grid,
        # The sum, not the max: every tile's decode was really paid for. Reporting one
        # tile's time would make tiling look free, which is the opposite of the trade.
        elapsed_ms=sum(p.elapsed_ms for p in per_tile),
    )


def _payload_arrays(
    prediction: Prediction,
) -> list[tuple[tuple[float, float, float, float], float, int]] | None:
    """Boxes, scores and class *indices*, or None when they do not line up.

    None rather than a guess: a misaligned payload means it was not built by
    `boxes_payload`, and pairing box *i* with score *j* is a silent mislabel.
    """
    payload = prediction.payload
    raw_boxes = payload.get("boxes")
    raw_scores = payload.get("scores")
    raw_classes = payload.get("classes")
    if not isinstance(raw_boxes, list) or not isinstance(raw_scores, list):
        return None
    if not isinstance(raw_classes, list):
        return None
    if not (len(raw_boxes) == len(raw_scores) == len(raw_classes)):
        return None

    return [
        ((float(box[0]), float(box[1]), float(box[2]), float(box[3])), float(score), int(index))
        for box, score, index in zip(raw_boxes, raw_scores, raw_classes, strict=True)
    ]


def _suppress(
    boxes: list[tuple[float, float, float, float]],
    scores: list[float],
    classes: list[int],
) -> list[int]:
    """Indices surviving class-aware NMS, highest score first.

    xywh to corners here and nowhere else: `batched_nms` wants xyxy and the rest of this
    project speaks xywh, so the conversion lives at the one call that needs it.
    """
    if not boxes:
        return []

    corners = torch.tensor(
        [[x, y, x + w, y + h] for x, y, w, h in boxes], dtype=torch.float32
    )
    keep = batched_nms(
        corners,
        torch.tensor(scores, dtype=torch.float32),
        torch.tensor(classes, dtype=torch.int64),
        NMS_IOU_THRESHOLD,
    )
    return [int(index) for index in keep[:MAX_DISPLAY_BOXES]]


__all__ = ["TILEABLE_HINT", "TileGrid", "merge_tiles", "run_tiled"]
