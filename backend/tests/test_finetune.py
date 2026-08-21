"""Fine-tuning a foundation detector (doc 44).

The parts worth pinning are the ones that fail *quietly*: a coordinate convention that
trains happily and predicts nonsense, a freeze that silently does nothing, and a cache that
hands the base model back as the fine-tune.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.ml.foundation.build import build_foundation, reset_cache
from app.ml.foundation.finetune import FinetuneConfig, to_detr_labels
from app.ml.foundation.instances import FoundationInstanceStore
from app.ml.training.samples import TrainingSample


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_cache()


class TestConfig:
    def test_it_needs_a_dataset(self) -> None:
        with pytest.raises(ValueError, match="dataset"):
            FinetuneConfig(foundation_id="rf-detr-nano", dataset_ids=(), name="x")

    def test_it_needs_a_name(self) -> None:
        # The name is what the model is called forever after; an empty one leaves a
        # picker entry the user cannot identify.
        with pytest.raises(ValueError, match="name"):
            FinetuneConfig(foundation_id="rf-detr-nano", dataset_ids=("d1",), name="  ")

    def test_defaults_are_fine_tuning_defaults_not_training_ones(self) -> None:
        """A COCO-pretrained decoder adapts in a handful of epochs at a low rate. The Head
        Trainer's 20 epochs at 1e-3 would be fitting a probe from scratch."""
        config = FinetuneConfig(foundation_id="rf-detr-nano", dataset_ids=("d1",), name="n")
        assert config.epochs <= 10
        assert config.learning_rate <= 1e-4

    def test_it_is_immutable(self) -> None:
        import dataclasses

        config = FinetuneConfig(foundation_id="rf-detr-nano", dataset_ids=("d1",), name="n")
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.epochs = 99  # type: ignore[misc]


class TestDetrLabelConversion:
    """The store speaks absolute xywh from the top-left; DETR wants normalised cxcywh.

    A missed conversion here does not raise — it trains, and predicts nonsense.
    """

    def _sample(self, targets: list[tuple[int, float, float, float, float]]) -> TrainingSample:
        return TrainingSample(path="/x.jpg", width=200, height=100, targets=tuple(targets))

    def test_a_centred_box_maps_to_the_centre(self) -> None:
        labels = to_detr_labels(self._sample([(0, 50.0, 25.0, 100.0, 50.0)]), "cpu")
        cx, cy, w, h = labels["boxes"][0].tolist()
        assert (cx, cy) == pytest.approx((0.5, 0.5))
        assert (w, h) == pytest.approx((0.5, 0.5))

    def test_everything_is_a_fraction_of_the_image(self) -> None:
        labels = to_detr_labels(self._sample([(0, 0.0, 0.0, 200.0, 100.0)]), "cpu")
        assert bool((labels["boxes"] >= 0).all() and (labels["boxes"] <= 1).all())

    def test_it_is_not_the_top_left_convention(self) -> None:
        # The decisive check: a box at the origin has centre (w/2, h/2), not (0, 0).
        labels = to_detr_labels(self._sample([(0, 0.0, 0.0, 100.0, 50.0)]), "cpu")
        cx, cy, _, _ = labels["boxes"][0].tolist()
        assert (cx, cy) == pytest.approx((0.25, 0.25))
        assert (cx, cy) != pytest.approx((0.0, 0.0))

    def test_class_labels_ride_alongside(self) -> None:
        labels = to_detr_labels(self._sample([(1, 0.0, 0.0, 10.0, 10.0)]), "cpu")
        assert labels["class_labels"].tolist() == [1]

    def test_a_degenerate_box_is_dropped_from_both_arrays(self) -> None:
        # Kept in one and not the other would misalign every later class.
        labels = to_detr_labels(
            self._sample([(0, 0.0, 0.0, 0.0, 10.0), (1, 10.0, 10.0, 20.0, 20.0)]), "cpu"
        )
        assert labels["boxes"].shape == (1, 4)
        assert labels["class_labels"].tolist() == [1]

    def test_an_image_with_no_boxes_gives_empty_but_shaped_tensors(self) -> None:
        """A background image is legitimate supervision; the matcher needs (0, 4), not (0,)."""
        labels = to_detr_labels(self._sample([]), "cpu")
        assert labels["boxes"].shape == (0, 4)
        assert labels["class_labels"].shape == (0,)


class TestTheInstanceStore:
    def _save(self, store: FoundationInstanceStore, name: str = "Thermal") -> str:
        instance = store.save(
            existing_id=None,
            name=name,
            base_model_id="rf-detr-nano",
            dataset_ids=("d1",),
            class_names=("dog", "person"),
            metrics={"map": 0.8},
            epochs_trained=6,
            save=lambda directory: (directory / "model.safetensors").write_bytes(b"\x00"),
        )
        return instance.id

    def test_a_saved_model_is_listed(self) -> None:
        store = FoundationInstanceStore()
        self._save(store)
        assert [i.name for i in store.list_all()] == ["Thermal"]

    def test_its_summary_says_what_it_came_from(self) -> None:
        store = FoundationInstanceStore()
        instance = store.get(self._save(store))
        assert instance is not None
        assert "rf-detr-nano" in instance.summary
        assert "map 0.800" in instance.summary

    def test_saving_again_with_the_same_id_replaces_it(self) -> None:
        """The runner saves on every improvement so a cancelled run keeps its best model.
        Without reuse that would leave a 115 MB directory per epoch."""
        store = FoundationInstanceStore()
        first = self._save(store)
        store.save(
            existing_id=first,
            name="Thermal",
            base_model_id="rf-detr-nano",
            dataset_ids=("d1",),
            class_names=("dog", "person"),
            metrics={"map": 0.9},
            epochs_trained=7,
            save=lambda directory: (directory / "model.safetensors").write_bytes(b"\x00"),
        )
        assert len(store.list_all()) == 1
        remaining = store.get(first)
        assert remaining is not None and remaining.metrics["map"] == 0.9

    def test_an_unreadable_manifest_does_not_break_the_listing(self) -> None:
        store = FoundationInstanceStore()
        good = self._save(store)
        broken = store.directory("broken")
        broken.mkdir(parents=True)
        (broken / "instance.json").write_text("{ not json")

        assert [i.id for i in store.list_all()] == [good] or good in [
            i.id for i in store.list_all()
        ]

    def test_a_traversal_id_is_refused(self) -> None:
        with pytest.raises(ValueError):
            FoundationInstanceStore().directory("../../etc")

    def test_deleting_removes_it(self) -> None:
        store = FoundationInstanceStore()
        instance_id = self._save(store)
        assert store.delete(instance_id) is True
        assert store.list_all() == []

    def test_the_manifest_round_trips(self) -> None:
        store = FoundationInstanceStore()
        instance_id = self._save(store)
        raw = json.loads((store.directory(instance_id) / "instance.json").read_text())
        assert raw["class_names"] == ["dog", "person"]
        assert raw["base_model_id"] == "rf-detr-nano"


class TestFineTuningDoesNotPoisonTheBaseModel:
    def test_a_fresh_build_is_not_the_cached_one(self) -> None:
        """The bug this pins, found by running it: `prepared_model` retargeted and then
        rewrote the *cached* `rf-detr-nano`, so every later request for the base detector
        returned the fine-tune — with its classes and its exact scores, which reads as a
        plausible result rather than a bug."""
        cached = build_foundation("rf-detr-nano")
        assert build_foundation("rf-detr-nano") is cached
        assert build_foundation("rf-detr-nano", fresh=True) is not cached

    def test_a_fresh_build_is_not_stored_in_the_cache(self) -> None:
        fresh = build_foundation("rf-detr-nano", fresh=True)
        assert build_foundation("rf-detr-nano") is not fresh
