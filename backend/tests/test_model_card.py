"""Model cards (doc 120): built from the stored record, never typed by hand."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
import torch

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.ml.foundation.instances import FoundationInstanceStore
from app.ml.heads.store import HeadInstanceStore
from app.mlops.card import CARD_SCHEMA, card_for


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_connection()
    yield tmp_path
    reset_connection()
    get_settings.cache_clear()


def _head(history: list[dict[str, object]] | None = None) -> str:
    instance = HeadInstanceStore().register(
        name="Screws",
        kind="trained-here",
        head_type_id="dense-detector",
        task="detection",
        backbone_id="dinov2-small",
        backbone_family="dinov2",
        embed_dim=384,
        num_classes=3,
        weights={"linear.weight": torch.randn(3, 8)},
        class_names=("m8", "m9", "m10"),
        dataset_ids=("gone",),
        metrics={"map": 0.5},
        primary_metric="map",
        primary_metric_value=0.5,
        config={"recipe_id": None, "epochs": 3},
        epochs_trained=3,
        best_epoch=2,
        history=history,
    )
    return instance.id


class TestHeadCard:
    def test_says_what_an_application_needs(self, isolated: Path) -> None:
        card = card_for("heads", _head())
        assert card["schema"] == CARD_SCHEMA
        assert card["classes"] == ["m8", "m9", "m10"]  # the stored order: index i is classes[i]
        assert card["base"]["repo_id"] == "facebook/dinov2-small"
        assert card["head"]["type_id"] == "dense-detector"
        assert "box distances" in card["outputs"]["decode"]
        assert card["training"]["datasets"] == [{"id": "gone", "name": "(deleted)"}]

    def test_weights_carry_a_checksum_and_no_local_folder(self, isolated: Path) -> None:
        card = card_for("heads", _head())
        [weights] = card["weights"]
        stored = next((isolated / "heads").glob("*.safetensors"))
        assert weights["file"] == stored.name
        assert weights["sha256"] == hashlib.sha256(stored.read_bytes()).hexdigest()
        assert str(isolated) not in str(card)

    def test_history_is_recorded_from_now_on(self, isolated: Path) -> None:
        epochs = [{"epoch": 1, "train_loss": 0.9, "val_loss": 1.0, "metrics": {"map": 0.3}}]
        assert card_for("heads", _head(epochs))["training"]["history"] == epochs
        older = card_for("heads", _head(None))["training"]
        assert older["history"] is None and "before Wave 15.6" in older["history_note"]

    def test_an_uninstalled_backbone_still_gives_a_card(self, isolated: Path) -> None:
        card = card_for("heads", _head())
        assert "not installed" in card["base"]["structure_note"]
        assert "not installed" in card["preprocessing"]["note"]

    def test_an_unknown_model_is_a_lookup_error(self, isolated: Path) -> None:
        with pytest.raises(LookupError):
            card_for("heads", "nope")


class TestFinetunedCard:
    def test_names_its_base_model_weights_and_baseline(self, isolated: Path) -> None:
        store = FoundationInstanceStore()
        saved = store.save(
            existing_id=None,
            name="outlines",
            base_model_id="sam2.1-hiera-small",
            dataset_ids=(),
            class_names=("ring",),
            metrics={"miou": 0.9},
            epochs_trained=2,
            save=lambda directory: (directory / "mask_decoder.safetensors").write_bytes(b"w"),
            finetune_id="sam2.1-hiera-small",
            baseline_metrics={"miou": 0.8},
            weights_kind="sam-mask-decoder",
            history=[{"epoch": 1, "train_loss": 0.4, "metrics": {"miou": 0.85}}],
        )
        card = card_for("finetuned", saved.id)
        assert card["model"]["kind"] == "finetuned"
        assert card["base"]["id"] == "sam2.1-hiera-small"
        # Not a backbone: no "not installed" note that would be false (found live).
        assert "structure_note" not in card["base"]
        assert card["weights_kind"] == "sam-mask-decoder"
        assert [w["file"] for w in card["weights"]] == ["mask_decoder.safetensors"]
        assert card["metrics"]["baseline"] == {"miou": 0.8}
        assert card["training"]["history"][0]["epoch"] == 1
