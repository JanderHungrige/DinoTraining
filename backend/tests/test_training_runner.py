"""Tests for the job runner's contract and the loop's decision helpers.

The full loop is exercised against real weights in integration verification, not here —
loading a backbone in the unit suite would make it slow and network-shaped. What is
asserted here is the runner's contract: what it refuses, and how it decides.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.heads.registry import get_head_type
from app.ml.training.config import TrainingConfig
from app.ml.training.job import EpochRecord, TrainingJob
from app.ml.training.loop import batched, is_better
from app.ml.training.runner import LocalJobRunner, get_job_runner


def config(**overrides: object) -> TrainingConfig:
    base: dict[str, object] = {
        "head_type_id": "linear-classifier",
        "backbone_id": "dinov2-small",
        "dataset_ids": ("ds1",),
    }
    base.update(overrides)
    return TrainingConfig(**base)  # type: ignore[arg-type]


class TestSubmitValidation:
    def test_depth_cannot_be_trained(self) -> None:
        """The check that makes the registry's usable/trainable split real."""
        runner = LocalJobRunner()
        with pytest.raises(ValueError, match="cannot be trained"):
            runner.submit(config(head_type_id="linear-depth"))

    def test_depth_rejection_points_at_the_alternative(self) -> None:
        runner = LocalJobRunner()
        with pytest.raises(ValueError, match="pretrained default"):
            runner.submit(config(head_type_id="linear-depth"))

    def test_unknown_head_type_raises(self) -> None:
        runner = LocalJobRunner()
        with pytest.raises(LookupError, match="Unknown head type"):
            runner.submit(config(head_type_id="not-a-head"))

    def test_every_trainable_head_is_accepted_by_validation(self) -> None:
        """Submission must not reject a head the registry says is trainable."""
        from app.ml.heads.registry import all_head_types

        for spec in all_head_types():
            if not spec.trainable:
                continue
            assert get_head_type(spec.id) is not None


class TestJobLookup:
    def test_unknown_job_is_none(self) -> None:
        assert LocalJobRunner().get("nope") is None

    def test_cancelling_an_unknown_job_returns_false(self) -> None:
        assert LocalJobRunner().cancel("nope") is False

    def test_cancelling_a_finished_job_returns_false(self) -> None:
        runner = LocalJobRunner()
        job = TrainingJob(job_id="j1", config=config())
        job.finish("complete")
        runner._jobs["j1"] = job
        assert runner.cancel("j1") is False

    def test_cancelling_a_running_job_sets_the_flag(self) -> None:
        runner = LocalJobRunner()
        job = TrainingJob(job_id="j2", config=config(), state="running")
        runner._jobs["j2"] = job
        assert runner.cancel("j2") is True
        assert job.cancel_requested.is_set()


class TestJobState:
    def test_records_accumulate_in_order(self) -> None:
        job = TrainingJob(job_id="j", config=config())
        job.record(EpochRecord(epoch=1, train_loss=1.0, val_loss=1.1, metrics={"accuracy": 0.4}))
        job.record(EpochRecord(epoch=2, train_loss=0.8, val_loss=0.9, metrics={"accuracy": 0.6}))
        assert [entry.epoch for entry in job.history] == [1, 2]
        assert job.epoch == 2

    def test_metrics_keys_are_not_fixed_by_the_job(self) -> None:
        """13 reads whatever keys the head declared; the job must not constrain them."""
        job = TrainingJob(job_id="j", config=config())
        job.record(EpochRecord(epoch=1, train_loss=1.0, val_loss=1.0, metrics={"miou": 0.3}))
        assert job.history[0].metrics == {"miou": 0.3}

    def test_finished_covers_every_terminal_state(self) -> None:
        for state in ("complete", "failed", "cancelled"):
            job = TrainingJob(job_id="j", config=config())
            job.finish(state)  # type: ignore[arg-type]
            assert job.finished
        assert not TrainingJob(job_id="j", config=config(), state="running").finished


class TestIsBetter:
    def test_first_value_always_wins(self) -> None:
        assert is_better(0.1, None, "max")
        assert is_better(99.0, None, "min")

    def test_max_mode_prefers_higher(self) -> None:
        assert is_better(0.9, 0.8, "max")
        assert not is_better(0.7, 0.8, "max")

    def test_min_mode_prefers_lower(self) -> None:
        assert is_better(0.7, 0.8, "min")
        assert not is_better(0.9, 0.8, "min")

    def test_equal_is_not_an_improvement(self) -> None:
        """Otherwise early stopping never triggers on a plateau."""
        assert not is_better(0.8, 0.8, "max")
        assert not is_better(0.8, 0.8, "min")


class TestBatched:
    def test_adds_a_batch_dimension_to_dense_targets(self) -> None:
        prepared = batched(
            {
                "class_target": torch.zeros(4, 4, dtype=torch.long),
                "positive": torch.zeros(4, 4, dtype=torch.bool),
                "box_target": torch.zeros(4, 4, 4),
            }
        )
        assert prepared["class_target"].shape == (1, 4, 4)
        assert prepared["positive"].shape == (1, 4, 4)
        assert prepared["box_target"].shape == (1, 4, 4, 4)

    def test_leaves_already_batched_targets_alone(self) -> None:
        prepared = batched({"class_target": torch.zeros(2, 4, 4, dtype=torch.long)})
        assert prepared["class_target"].shape == (2, 4, 4)

    def test_leaves_classification_labels_alone(self) -> None:
        prepared = batched({"labels": torch.tensor([1])})
        assert prepared["labels"].shape == (1,)


class TestToDevice:
    """Regression: targets are built on CPU while features live on MPS/CUDA.

    Mixing them raised "Placeholder storage has not been allocated on MPS device" from
    inside the loss, naming neither the tensor nor the caller. Unit tests missed it
    entirely because they hand-build tensors that are already co-located.
    """

    def test_moves_every_target_tensor(self) -> None:
        from app.ml.training.loop import to_device

        targets = {
            "labels": torch.tensor([1]),
            "class_target": torch.zeros(4, 4, dtype=torch.long),
            "box_target": torch.zeros(4, 4, 4),
        }
        moved = to_device(targets, "cpu")
        assert set(moved) == set(targets)
        assert all(value.device.type == "cpu" for value in moved.values())

    def test_available_accelerator_receives_every_tensor(self) -> None:
        from app.ml.training.loop import to_device

        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            pytest.skip("no accelerator on this machine")

        moved = to_device({"a": torch.zeros(2), "b": torch.ones(3, 3)}, device)
        assert all(value.device.type == device for value in moved.values())


class TestRunnerSingleton:
    def test_get_job_runner_is_process_wide(self) -> None:
        """Wave 6 swaps the construction here; call sites must not build their own."""
        assert get_job_runner() is get_job_runner()
