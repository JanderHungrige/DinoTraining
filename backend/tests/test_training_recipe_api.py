"""Starting training and fine-tuning from a recipe, through the API (doc 90)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.v1 import training as training_api
from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.datasets.models import Box, ImageAnnotation
from app.datasets.store import DatasetStore
from app.main import create_app
from app.ml.training.config import TrainingConfig
from app.ml.training.job import TrainingJob
from app.prep.audit import run_audit
from app.prep.fixes import set_excluded
from app.prep.recipe import RecipeRequest, save_recipe
from app.prep.split_service import make_split


class RecordingRunner:
    def __init__(self) -> None:
        self.configs: list[TrainingConfig] = []

    def submit(self, config: TrainingConfig) -> TrainingJob:
        self.configs.append(config)
        return TrainingJob(job_id="j", config=config)


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> RecordingRunner:
    recording = RecordingRunner()
    monkeypatch.setattr(training_api, "get_job_runner", lambda: recording)
    return recording


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_connection()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_connection()
    get_settings.cache_clear()


def _recipe(tmp_path: Path) -> tuple[str, str]:
    store = DatasetStore()
    dataset_id = store.create("Cells", None, False).id
    for i in range(10):
        path = tmp_path / f"c{i}.png"
        Image.effect_noise((64, 48), 30 + i * 9).convert("RGB").save(path)
        box = Box(label="positive", provenance="hand-drawn", prompt="cell", x=4, y=4, w=20, h=20)
        store.replace_image_boxes(
            dataset_id, ImageAnnotation(path=str(path), width=64, height=48, boxes=[box])
        )
    run_audit(dataset_id, "head-detection-dinov2", lambda done, total: None)
    make_split(dataset_id)
    request = RecipeRequest(
        name="cells", target="head-detection-dinov2", imbalance="weighted-loss",
        augmentation="microscopy",
    )  # fmt: skip
    return dataset_id, save_recipe(dataset_id, request).id


def _train(
    client: TestClient, dataset_ids: list[str], recipe_id: str, head: str = "dense-detector"
):
    return client.post(
        "/api/v1/training/jobs",
        json={
            "head_type_id": head,
            "backbone_id": "dinov2-small",
            "dataset_ids": dataset_ids,
            "recipe_id": recipe_id,
        },
    )


def test_a_recipe_sets_the_run_and_is_named_in_it(
    client: TestClient, runner: RecordingRunner, tmp_path: Path
) -> None:
    dataset_id, recipe_id = _recipe(tmp_path)
    response = _train(client, [dataset_id], recipe_id)
    assert response.status_code == 202, response.json()
    config = runner.configs[0]
    assert (config.recipe_id, config.imbalance, config.augmentation) == (
        recipe_id,
        "weighted-loss",
        "microscopy",
    )
    assert response.json()["recipe_id"] == recipe_id


def test_a_recipe_that_no_longer_describes_the_data_is_refused_with_the_reason(
    client: TestClient, runner: RecordingRunner, tmp_path: Path
) -> None:
    dataset_id, recipe_id = _recipe(tmp_path)
    set_excluded(dataset_id, [str(tmp_path / "c0.png")], True)
    response = _train(client, [dataset_id], recipe_id)
    assert response.status_code == 409
    assert "exclusions changed" in str(response.json())
    assert runner.configs == []


def test_a_recipe_must_fit_the_model_and_the_datasets(
    client: TestClient, runner: RecordingRunner, tmp_path: Path
) -> None:
    dataset_id, recipe_id = _recipe(tmp_path)
    wrong_task = _train(client, [dataset_id], recipe_id, head="linear-classifier")
    assert wrong_task.status_code == 422 and "prepared for" in str(wrong_task.json())
    two = _train(client, [dataset_id, "other"], recipe_id)
    assert two.status_code == 422 and "one dataset" in str(two.json())
    assert _train(client, [dataset_id], "nope").status_code == 404
    finetune = client.post(
        "/api/v1/foundation/finetune",
        json={"foundation_id": "rf-detr-nano", "dataset_ids": [dataset_id], "name": "x",
              "recipe_id": "nope"},
    )  # fmt: skip
    assert finetune.status_code == 404
