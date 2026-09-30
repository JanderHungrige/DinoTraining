"""Class-imbalance mechanics: weights, repeat factors, weighted losses (doc 86)."""

from __future__ import annotations

import random
from collections import Counter

import pytest
import torch

from app.ml.heads.registry import get_head_type
from app.ml.training.config import TrainingConfig
from app.ml.training.imbalance import (
    MAX_WEIGHT,
    class_counts,
    class_weights,
    epoch_indices,
    plan_balance,
    repeat_factors,
    sample_classes,
)
from app.ml.training.losses import classification_loss, detection_loss, segmentation_loss
from app.ml.training.samples import MaskTarget, TrainingSample


def test_weights_favour_the_rare_class_and_average_one() -> None:
    weights = class_weights([400, 100, 0])
    assert weights[1] == pytest.approx(2 * weights[0])  # sqrt(400/100)
    assert (weights[0] + weights[1]) / 2 == pytest.approx(1.0)
    assert weights[2] == 1.0  # absent: nothing to weight


def test_a_single_example_cannot_outweigh_everything() -> None:
    # With two classes the mean-1 normalisation already bounds the rare weight below 2;
    # the cap matters with many classes, where the rare one would reach ~20 here.
    assert max(class_weights([100_000] * 20 + [1])) == MAX_WEIGHT


def test_images_with_rare_classes_repeat_by_the_root_of_the_ratio() -> None:
    presence = [{0}] * 16 + [{0, 1}] + [set()]
    factors = repeat_factors(presence)
    assert factors[0] == 1.0
    assert factors[16] == pytest.approx(17**0.5)  # holds the rare class
    assert factors[17] == 1.0  # background image: shown once


def test_an_epoch_visits_rare_images_about_that_often_and_is_reproducible() -> None:
    factors = [1.0] * 10 + [2.5]
    visits = [Counter(epoch_indices(range(11), factors, random.Random(e)))[10] for e in range(400)]
    assert 2.4 < sum(visits) / len(visits) < 2.6
    assert set(visits) == {2, 3}
    assert epoch_indices(range(11), factors, random.Random(7)) == epoch_indices(
        range(11), factors, random.Random(7)
    )


def boxes(*classes: int) -> TrainingSample:
    return TrainingSample("/x.jpg", 10, 10, targets=tuple((c, 0.0, 0.0, 1.0, 1.0) for c in classes))


def test_counts_are_objects_over_the_training_indices_only() -> None:
    # Blood cells' shape: the rare class shares every image with the common one. Counted
    # by image the two look equal; counted by object they are not (found live).
    samples = [boxes(0, 0, 0, 0, 1), boxes(0, 0, 0, 0), boxes(1, 1)]
    assert class_counts(samples, [0, 1], "detection", 2) == [8, 1]


def test_segmentation_classes_sit_behind_the_background() -> None:
    sample = TrainingSample(
        "/x.jpg", 10, 10, masks=(MaskTarget(class_index=0, counts=(100,), size=(10, 10)),)
    )
    assert sample_classes(sample, "segmentation") == {1}
    assert sample_classes(TrainingSample("/y.jpg", 1, 1, image_class=2), "classification") == {2}


def test_a_rare_class_mistake_costs_more_with_weights() -> None:
    # Both images predicted as class 0: wrong for the rare class 1, right for class 0.
    batch = {"logits": torch.tensor([[2.0, 0.0], [2.0, 0.0]])}
    labels = {"labels": torch.tensor([1, 0])}
    weights = torch.tensor([0.5, 1.5])
    assert float(classification_loss(batch, labels, weights)) > float(
        classification_loss(batch, labels)
    )


def test_unit_weights_leave_detection_and_segmentation_unchanged() -> None:
    torch.manual_seed(0)
    outputs = {
        "class_logits": torch.randn(1, 2, 4, 4),
        "box_ltrb": torch.rand(1, 4, 4, 4) + 0.1,
        "centerness": torch.randn(1, 1, 4, 4),
    }
    class_target = torch.full((1, 4, 4), -1)
    class_target[0, 1, 1] = 1
    targets = {
        "class_target": class_target,
        "positive": class_target >= 0,
        "box_target": torch.rand(1, 4, 4, 4) + 0.1,
    }
    ones = torch.ones(2)
    assert float(detection_loss(outputs, targets, ones)) == pytest.approx(
        float(detection_loss(outputs, targets))
    )
    heavier = float(detection_loss(outputs, targets, torch.tensor([1.0, 5.0])))
    assert heavier > float(detection_loss(outputs, targets))

    seg_out = {"logits": torch.randn(1, 3, 4, 4)}
    seg_target = {"mask": torch.randint(0, 3, (1, 4, 4))}
    assert float(segmentation_loss(seg_out, seg_target, torch.ones(3))) == pytest.approx(
        float(segmentation_loss(seg_out, seg_target))
    )


def test_the_plan_binds_weights_or_factors_or_neither() -> None:
    spec = get_head_type("linear-classifier")
    assert spec is not None
    samples = [TrainingSample(f"/{i}.jpg", 1, 1, image_class=0) for i in range(9)]
    samples.append(TrainingSample("/9.jpg", 1, 1, image_class=1))
    none = plan_balance("none", spec, samples, range(10), 2, 42)
    assert none.factors is None and none.order(range(10), 1) == tuple(range(10))
    sampled = plan_balance("balanced-sampling", spec, samples, range(10), 2, 42)
    assert sampled.order(range(10), 1).count(9) >= 3  # sqrt(9) = 3
    weighted = plan_balance("weighted-loss", spec, samples, range(10), 2, 42)
    assert weighted.factors is None


def test_an_unknown_strategy_is_refused_by_the_config() -> None:
    with pytest.raises(ValueError, match="imbalance"):
        TrainingConfig(
            head_type_id="linear-classifier",
            backbone_id="dinov2-small",
            dataset_ids=("d",),
            imbalance="shuffle-harder",
        )
