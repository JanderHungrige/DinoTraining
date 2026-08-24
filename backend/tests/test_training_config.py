"""Tests for training config validation and deterministic splitting.

Splitting by image rather than box is the load-bearing rule: boxes from one image in
both train and val is leakage that inflates validation with no visible symptom.
"""

from __future__ import annotations

import pytest

from app.ml.training.config import TrainingConfig, split_indices


def config(**overrides: object) -> TrainingConfig:
    base: dict[str, object] = {
        "head_type_id": "linear-classifier",
        "backbone_id": "dinov2-small",
        "dataset_ids": ("ds1",),
    }
    base.update(overrides)
    return TrainingConfig(**base)  # type: ignore[arg-type]


class TestValidation:
    def test_defaults_are_usable_without_any_decision(self) -> None:
        """The demo-state requires a user to press Train without configuring anything."""
        built = config()
        assert built.epochs > 0
        assert built.save_best_only is True
        assert built.augment is False  # so the feature cache applies

    def test_requires_a_dataset(self) -> None:
        with pytest.raises(ValueError, match="dataset"):
            config(dataset_ids=())

    def test_rejects_zero_epochs(self) -> None:
        with pytest.raises(ValueError, match="epochs"):
            config(epochs=0)

    def test_rejects_zero_batch_size(self) -> None:
        with pytest.raises(ValueError, match="batch_size"):
            config(batch_size=0)

    def test_rejects_non_positive_learning_rate(self) -> None:
        with pytest.raises(ValueError, match="learning_rate"):
            config(learning_rate=0.0)

    def test_rejects_splits_that_leave_no_training_data(self) -> None:
        """Otherwise the run fails minutes later with a confusing 'no samples'."""
        with pytest.raises(ValueError, match="training split"):
            config(val_fraction=0.7, test_fraction=0.3)

    def test_rejects_zero_patience(self) -> None:
        with pytest.raises(ValueError, match="patience"):
            config(early_stopping_patience=0)

    def test_is_frozen(self) -> None:
        import dataclasses

        with pytest.raises(dataclasses.FrozenInstanceError):
            config().epochs = 5  # type: ignore[misc]


class TestSplitIndices:
    def test_partitions_every_index_exactly_once(self) -> None:
        split = split_indices(100, 0.2, 0.1, seed=1)
        combined = sorted([*split.train, *split.val, *split.test])
        assert combined == list(range(100))

    def test_is_deterministic_for_a_seed(self) -> None:
        assert split_indices(50, 0.2, 0.1, seed=7) == split_indices(50, 0.2, 0.1, seed=7)

    def test_different_seeds_give_different_splits(self) -> None:
        assert split_indices(50, 0.2, 0.1, seed=1) != split_indices(50, 0.2, 0.1, seed=2)

    def test_respects_requested_proportions(self) -> None:
        split = split_indices(100, 0.2, 0.1, seed=3)
        assert len(split.val) == 20
        assert len(split.test) == 10
        assert len(split.train) == 70

    def test_tiny_dataset_still_yields_a_validation_sample(self) -> None:
        """A val split rounded to zero silently disables early stopping and best-model."""
        split = split_indices(5, 0.2, 0.0, seed=1)
        assert len(split.val) >= 1
        assert len(split.train) >= 1

    def test_training_split_is_never_empty(self) -> None:
        for count in range(1, 12):
            split = split_indices(count, 0.2, 0.1, seed=1)
            assert len(split.train) >= 1, count

    def test_empty_dataset_yields_empty_splits(self) -> None:
        split = split_indices(0, 0.2, 0.1, seed=1)
        assert split.train == () and split.val == () and split.test == ()

    def test_zero_fractions_put_everything_in_train(self) -> None:
        split = split_indices(10, 0.0, 0.0, seed=1)
        assert len(split.train) == 10
        assert split.val == () and split.test == ()
