"""Tests for head-instance persistence and the summary contract.

The summary is what every picker in Waves 3 and 4 renders, so it is tested as a
contract rather than a formatting detail: a head must never be presentable as a bare
filename.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import torch

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.ml.heads.instances import HeadInstance
from app.ml.heads.store import (
    HeadInstanceNotFoundError,
    HeadInstanceStore,
    heads_root,
)


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[HeadInstanceStore]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    reset_connection()
    yield HeadInstanceStore()
    reset_connection()
    get_settings.cache_clear()


def weights() -> dict[str, torch.Tensor]:
    return {"linear.weight": torch.randn(3, 8), "linear.bias": torch.zeros(3)}


def register(store: HeadInstanceStore, **overrides: object) -> HeadInstance:
    base: dict[str, object] = {
        "name": "Detector",
        "kind": "trained-here",
        "head_type_id": "dense-detector",
        "task": "detection",
        "backbone_id": "dinov2-small",
        "backbone_family": "dinov2",
        "embed_dim": 384,
        "num_classes": 2,
        "weights": weights(),
        "class_names": ("a cat", "a dog"),
        "dataset_ids": ("ds1",),
        "metrics": {"map": 0.52, "map_50": 0.95},
        "primary_metric": "map",
        "primary_metric_value": 0.52,
    }
    base.update(overrides)
    return store.register(**base)  # type: ignore[arg-type]


class TestRegister:
    def test_returns_a_persisted_instance(self, store: HeadInstanceStore) -> None:
        instance = register(store)
        assert instance.id
        assert store.get(instance.id).name == "Detector"

    def test_writes_a_safetensors_file(self, store: HeadInstanceStore) -> None:
        """Safetensors even for our own heads: no pickle path exists for anything."""
        instance = register(store)
        assert Path(instance.weights_path).is_file()
        assert instance.weights_path.endswith(".safetensors")

    def test_weights_round_trip(self, store: HeadInstanceStore) -> None:
        original = weights()
        instance = register(store, weights=original)
        loaded = store.load_weights(instance.id)
        assert set(loaded) == set(original)
        assert torch.allclose(loaded["linear.bias"], original["linear.bias"])

    def test_class_order_is_preserved(self, store: HeadInstanceStore) -> None:
        """Index 3 in the weights means whatever index 3 meant at training time."""
        instance = register(store, class_names=("zebra", "ant", "moose"), num_classes=3)
        assert store.get(instance.id).class_names == ("zebra", "ant", "moose")

    def test_trained_head_without_classes_is_refused(self, store: HeadInstanceStore) -> None:
        with pytest.raises(ValueError, match="class order"):
            register(store, class_names=())

    def test_imported_head_may_have_no_classes(self, store: HeadInstanceStore) -> None:
        instance = register(
            store, kind="pretrained-default", class_names=(), num_classes=0,
            task="depth", head_type_id="linear-depth", source_repo="facebook/dinov2",
        )
        assert instance.kind == "pretrained-default"

    def test_config_snapshot_survives(self, store: HeadInstanceStore) -> None:
        """Without it a checkpoint records what it achieved but not how."""
        instance = register(store, config={"epochs": 12, "learning_rate": 0.01})
        assert store.get(instance.id).config["epochs"] == 12

    def test_weights_are_confined_to_the_heads_directory(
        self, store: HeadInstanceStore
    ) -> None:
        instance = register(store)
        assert Path(instance.weights_path).parent == heads_root()


class TestListAndFilter:
    def test_lists_everything_by_default(self, store: HeadInstanceStore) -> None:
        register(store)
        register(store, task="classification", head_type_id="linear-classifier")
        assert len(store.list_all()) == 2

    def test_filters_by_task(self, store: HeadInstanceStore) -> None:
        """This is what powers same-task comparison in Wave 3."""
        register(store)
        register(store, task="classification", head_type_id="linear-classifier")
        found = store.list_all(task="detection")
        assert [i.task for i in found] == ["detection"]

    def test_filters_by_backbone(self, store: HeadInstanceStore) -> None:
        register(store)
        register(store, backbone_id="dinov2-base")
        assert len(store.list_all(backbone_id="dinov2-base")) == 1

    def test_combines_filters(self, store: HeadInstanceStore) -> None:
        register(store)
        register(store, task="classification", head_type_id="linear-classifier")
        assert store.list_all(task="detection", backbone_id="dinov2-small")
        assert not store.list_all(task="detection", backbone_id="dinov2-large")

    def test_empty_store_lists_nothing(self, store: HeadInstanceStore) -> None:
        assert store.list_all() == []


class TestGetAndDelete:
    def test_unknown_id_raises(self, store: HeadInstanceStore) -> None:
        with pytest.raises(HeadInstanceNotFoundError):
            store.get("nope")

    def test_delete_removes_row_and_weights(self, store: HeadInstanceStore) -> None:
        """An orphaned weights file is invisible disk the Admin tab cannot account for."""
        instance = register(store)
        path = Path(instance.weights_path)
        assert store.delete(instance.id) is True
        assert not path.exists()
        assert not store.exists(instance.id)

    def test_delete_is_idempotent(self, store: HeadInstanceStore) -> None:
        assert store.delete("never-existed") is False

    def test_exists_reports_accurately(self, store: HeadInstanceStore) -> None:
        instance = register(store)
        assert store.exists(instance.id)
        store.delete(instance.id)
        assert not store.exists(instance.id)


class TestSummary:
    """The cross-tab contract: a head is described by what it does, never a filename."""

    def make(self, **overrides: object) -> HeadInstance:
        base: dict[str, object] = {
            "id": "abc",
            "name": "n",
            "kind": "trained-here",
            "head_type_id": "dense-detector",
            "task": "detection",
            "backbone_id": "dinov2-small",
            "backbone_family": "dinov2",
            "embed_dim": 384,
            "num_classes": 2,
            "weights_path": "/tmp/x.safetensors",
            "created_at": "2026-08-18T00:00:00+00:00",
        }
        base.update(overrides)
        return HeadInstance(**base)  # type: ignore[arg-type]

    def test_names_the_task_in_words(self) -> None:
        assert self.make().summary.startswith("Object detection")

    def test_includes_class_count_and_training_data(self) -> None:
        summary = self.make(
            class_names=("a", "b"), dataset_ids=("ds1",),
            primary_metric="map", primary_metric_value=0.523,
        ).summary
        assert "2 classes" in summary
        assert "trained on 1 dataset" in summary
        assert "map 0.523" in summary

    def test_singular_class_reads_correctly(self) -> None:
        summary = self.make(num_classes=1, class_names=("a",)).summary
        assert "1 class" in summary
        assert "1 classes" not in summary

    def test_pretrained_default_names_its_source(self) -> None:
        summary = self.make(
            kind="pretrained-default", task="depth", num_classes=0,
            source_repo="facebook/dinov2",
        ).summary
        assert "Depth estimation" in summary
        assert "pretrained default (facebook/dinov2)" in summary

    def test_community_head_is_labelled(self) -> None:
        assert "community" in self.make(kind="community", source_repo="someone/head").summary

    def test_never_contains_the_weights_filename(self) -> None:
        """The whole point: the user must never choose between two hex filenames."""
        summary = self.make(weights_path="/data/heads/deadbeef.safetensors").summary
        assert "deadbeef" not in summary
        assert ".safetensors" not in summary


class TestSchemaMigration:
    def test_head_instances_table_exists_on_a_fresh_database(
        self, store: HeadInstanceStore
    ) -> None:
        """executescript with IF NOT EXISTS migrates existing Wave 1 databases in place."""
        from app.datasets.db import transaction

        with transaction() as connection:
            row = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='head_instances'"
            ).fetchone()
        assert row is not None

    def test_kind_is_check_constrained(self, store: HeadInstanceStore) -> None:
        import sqlite3

        from app.datasets.db import transaction

        with pytest.raises(sqlite3.IntegrityError), transaction() as connection:
            connection.execute(
                "INSERT INTO head_instances (id, name, kind, head_type_id, task, backbone_id,"
                " backbone_family, embed_dim, num_classes, weights_path, created_at)"
                " VALUES ('x','n','not-a-kind','h','t','b','f',1,1,'/p','now')"
            )

    def test_json_columns_round_trip(self, store: HeadInstanceStore) -> None:
        instance = register(store, metrics={"map": 0.5, "map_50": 0.9})
        assert json.loads(json.dumps(store.get(instance.id).metrics)) == {
            "map": 0.5,
            "map_50": 0.9,
        }
