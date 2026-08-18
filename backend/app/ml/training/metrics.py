"""Metric computation, keyed by head type.

Implemented directly rather than pulled from torchmetrics: the project ships as a
desktop app and every added dependency is weight in the installer. These are the exact
metric names each head type declares in `08`, so the stream in `13` reads keys rather
than hardcoding them.
"""

from __future__ import annotations

from collections.abc import Callable

import torch
from torch import Tensor

from app.ml.heads.registry import HeadTypeSpec
from app.ml.training.losses import IGNORE_INDEX

#: (predictions, targets) -> named metric values.
MetricFn = Callable[[list[dict[str, Tensor]], list[dict[str, Tensor]]], dict[str, float]]


def classification_metrics(
    outputs: list[dict[str, Tensor]], targets: list[dict[str, Tensor]]
) -> dict[str, float]:
    """Accuracy and macro-F1.

    Macro-F1 averages over classes rather than samples, so a model that ignores a rare
    class is penalised — accuracy alone would hide that on an imbalanced dataset, which
    hand-annotated datasets almost always are.
    """
    if not outputs:
        return {"accuracy": 0.0, "macro_f1": 0.0}

    predictions = torch.cat([out["logits"].argmax(dim=1) for out in outputs])
    truth = torch.cat([tgt["labels"] for tgt in targets])
    if predictions.numel() == 0:
        return {"accuracy": 0.0, "macro_f1": 0.0}

    accuracy = float((predictions == truth).float().mean())

    f1_scores: list[float] = []
    for class_index in torch.unique(truth):
        predicted_positive = predictions == class_index
        actually_positive = truth == class_index
        true_positive = float((predicted_positive & actually_positive).sum())
        precision_den = float(predicted_positive.sum())
        recall_den = float(actually_positive.sum())
        precision = true_positive / precision_den if precision_den else 0.0
        recall = true_positive / recall_den if recall_den else 0.0
        f1_scores.append(
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )

    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    return {"accuracy": accuracy, "macro_f1": macro_f1}


def segmentation_metrics(
    outputs: list[dict[str, Tensor]], targets: list[dict[str, Tensor]]
) -> dict[str, float]:
    """Mean IoU and pixel accuracy, skipping ignored pixels.

    Ignored pixels are excluded from both. Counting letterbox padding as correct
    background would inflate pixel accuracy toward 1.0 on tall or wide images and make
    the number meaningless.
    """
    intersections: dict[int, float] = {}
    unions: dict[int, float] = {}
    correct = 0.0
    total = 0.0

    for out, tgt in zip(outputs, targets, strict=True):
        logits = out["logits"]
        mask = tgt["mask"].long()
        if logits.shape[-2:] != mask.shape[-2:]:
            logits = torch.nn.functional.interpolate(
                logits, size=mask.shape[-2:], mode="bilinear", align_corners=False
            )
        predicted = logits.argmax(dim=1)

        valid = mask != IGNORE_INDEX
        correct += float((predicted[valid] == mask[valid]).sum())
        total += float(valid.sum())

        for class_index in torch.unique(mask[valid]).tolist():
            predicted_class = (predicted == class_index) & valid
            true_class = (mask == class_index) & valid
            intersections[class_index] = intersections.get(class_index, 0.0) + float(
                (predicted_class & true_class).sum()
            )
            unions[class_index] = unions.get(class_index, 0.0) + float(
                (predicted_class | true_class).sum()
            )

    ious = [intersections[c] / unions[c] for c in unions if unions[c] > 0]
    return {
        "miou": sum(ious) / len(ious) if ious else 0.0,
        "pixel_accuracy": correct / total if total else 0.0,
    }


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """IoU of two xywh boxes."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    left, top = max(ax, bx), max(ay, by)
    right, bottom = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if right <= left or bottom <= top:
        return 0.0
    overlap = (right - left) * (bottom - top)
    return overlap / (aw * ah + bw * bh - overlap)


def average_precision(
    predictions: list[tuple[float, tuple[float, float, float, float], int]],
    ground_truth: list[tuple[tuple[float, float, float, float], int]],
    threshold: float,
) -> float:
    """All-point-interpolated AP at one IoU threshold, averaged over classes.

    Each ground-truth box may be matched once; later, lower-scoring detections of the
    same object count as false positives. Without that rule a model that emits the same
    box fifty times would score a perfect AP.
    """
    classes = {cls for _, cls in ground_truth} | {cls for _, _, cls in predictions}
    if not classes:
        return 0.0

    per_class: list[float] = []
    for class_index in sorted(classes):
        truths = [box for box, cls in ground_truth if cls == class_index]
        detections = sorted(
            [(score, box) for score, box, cls in predictions if cls == class_index],
            key=lambda item: item[0],
            reverse=True,
        )
        if not truths:
            per_class.append(0.0)
            continue

        matched = [False] * len(truths)
        true_positives: list[float] = []
        false_positives: list[float] = []

        for _, box in detections:
            best_iou, best_index = 0.0, -1
            for index, truth in enumerate(truths):
                if matched[index]:
                    continue
                overlap = _iou(box, truth)
                if overlap > best_iou:
                    best_iou, best_index = overlap, index
            if best_iou >= threshold and best_index >= 0:
                matched[best_index] = True
                true_positives.append(1.0)
                false_positives.append(0.0)
            else:
                true_positives.append(0.0)
                false_positives.append(1.0)

        if not detections:
            per_class.append(0.0)
            continue

        cumulative_tp = torch.tensor(true_positives).cumsum(dim=0)
        cumulative_fp = torch.tensor(false_positives).cumsum(dim=0)
        recalls = cumulative_tp / len(truths)
        precisions = cumulative_tp / (cumulative_tp + cumulative_fp).clamp(min=1e-9)

        # All-point interpolation: precision is made monotonically decreasing before
        # integrating, so a late precision spike cannot inflate the earlier curve.
        precisions = torch.flip(torch.cummax(torch.flip(precisions, [0]), dim=0).values, [0])
        previous_recall = 0.0
        area = 0.0
        for recall, precision in zip(recalls.tolist(), precisions.tolist(), strict=True):
            area += (recall - previous_recall) * precision
            previous_recall = recall
        per_class.append(area)

    return sum(per_class) / len(per_class) if per_class else 0.0


def detection_metrics(
    outputs: list[dict[str, Tensor]], targets: list[dict[str, Tensor]]
) -> dict[str, float]:
    """mAP at 0.5, 0.75 and their mean.

    ``outputs`` carry decoded ``boxes``/``scores``/``classes``; the runner decodes once
    via ``decode_ltrb_to_boxes`` so this never re-derives the box convention.
    """
    predictions: list[tuple[float, tuple[float, float, float, float], int]] = []
    ground_truth: list[tuple[tuple[float, float, float, float], int]] = []

    for out, tgt in zip(outputs, targets, strict=True):
        for score, box, cls in zip(
            out["scores"].tolist(), out["boxes"].tolist(), out["classes"].tolist(), strict=True
        ):
            predictions.append((float(score), (box[0], box[1], box[2], box[3]), int(cls)))
        for box, cls in zip(tgt["boxes"].tolist(), tgt["classes"].tolist(), strict=True):
            ground_truth.append(((box[0], box[1], box[2], box[3]), int(cls)))

    map_50 = average_precision(predictions, ground_truth, 0.5)
    map_75 = average_precision(predictions, ground_truth, 0.75)
    return {"map": (map_50 + map_75) / 2, "map_50": map_50, "map_75": map_75}


METRICS: dict[str, MetricFn] = {
    "linear-classifier": classification_metrics,
    "dense-detector": detection_metrics,
    "linear-segmenter": segmentation_metrics,
}


def metrics_for(spec: HeadTypeSpec) -> MetricFn:
    """The metric function for a head type."""
    metric = METRICS.get(spec.id)
    if metric is None:
        raise LookupError(f"No metrics registered for {spec.id}")
    return metric
