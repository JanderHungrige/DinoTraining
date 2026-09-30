"""Preparation recipes through the real ASGI app (doc 88)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.main import create_app
from app.prep.jobs import reset_prep_runner


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_prep_runner()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_prep_runner()
    get_settings.cache_clear()


def _dataset(client: TestClient, tmp_path: Path) -> tuple[str, list[str]]:
    dataset_id = str(client.post("/api/v1/datasets", json={"name": "Recipe"}).json()["id"])
    paths = []
    for index in range(12):
        path = tmp_path / f"r{index}.png"
        # Distinct pictures, so no two are grouped as one scene.
        Image.effect_noise((64, 48), 40 + index * 7).convert("RGB").save(path)
        box = {
            "label": "positive",
            "provenance": "hand-drawn",
            "prompt": "car" if index % 3 else "bus",
        }
        body = {
            "path": str(path),
            "width": 64,
            "height": 48,
            "boxes": [box | {"x": 5, "y": 5, "w": 30, "h": 20}],
        }
        assert client.put(f"/api/v1/datasets/{dataset_id}/images", json=body).status_code == 200
        paths.append(str(path))
    return dataset_id, paths


def _audit(client: TestClient, dataset_id: str) -> None:
    job = client.post(f"/api/v1/datasets/{dataset_id}/audit", json={"target": "rf-detr-nano"})
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if client.get(f"/api/v1/prep/audits/{job.json()['job_id']}").json()["state"] == "complete":
            return
        time.sleep(0.05)
    raise AssertionError("audit did not finish")


RECIPE = {
    "name": "first try",
    "target": "head-detection-dinov2",
    "imbalance": "weighted-loss",
    "augmentation": "general",
}


def test_a_recipe_needs_each_step_and_says_which_is_missing(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id, _ = _dataset(client, tmp_path)
    url = f"/api/v1/datasets/{dataset_id}/recipes"
    refused = client.post(url, json=RECIPE)
    assert refused.status_code == 409 and "Audit step" in str(refused.json())
    _audit(client, dataset_id)
    refused = client.post(url, json=RECIPE)
    assert refused.status_code == 409 and "Split step" in str(refused.json())
    assert client.post(url, json=RECIPE | {"imbalance": "magic"}).status_code == 422


def test_a_saved_recipe_records_everything_and_versions_by_name(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id, _ = _dataset(client, tmp_path)
    _audit(client, dataset_id)
    client.post(f"/api/v1/datasets/{dataset_id}/split", json={"seed": 7})
    url = f"/api/v1/datasets/{dataset_id}/recipes"
    first = client.post(url, json=RECIPE)
    assert first.status_code == 201
    recipe = first.json()["recipe"]
    assert recipe["version"] == 1 and recipe["split"]["seed"] == 7
    assert sum(recipe["split"]["sides"].values()) + recipe["split"]["buffer"] == 12
    assert recipe["fit"] == "letterbox" and recipe["input_size"] == 448
    assert (recipe["imbalance"], recipe["augmentation"]) == ("weighted-loss", "general")
    second = client.post(url, json=RECIPE).json()["recipe"]
    assert second["version"] == 2 and second["id"] != recipe["id"]
    listed = client.get(url).json()
    assert [r["recipe"]["version"] for r in listed] == [1, 2]
    assert all(r["out_of_date"] == [] for r in listed)


def test_a_recipe_notices_when_the_data_or_split_changes(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id, paths = _dataset(client, tmp_path)
    _audit(client, dataset_id)
    client.post(f"/api/v1/datasets/{dataset_id}/split", json={})
    recipe_id = client.post(f"/api/v1/datasets/{dataset_id}/recipes", json=RECIPE).json()["recipe"][
        "id"
    ]
    one = f"/api/v1/datasets/{dataset_id}/recipes/{recipe_id}"

    client.post(
        f"/api/v1/datasets/{dataset_id}/fixes", json={"action": "exclude", "paths": [paths[0]]}
    )
    assert "exclusions changed" in client.get(one).json()["out_of_date"][0]
    client.post(
        f"/api/v1/datasets/{dataset_id}/fixes", json={"action": "include", "paths": [paths[0]]}
    )
    assert client.get(one).json()["out_of_date"] == []  # undone: describes the data again

    client.post(f"/api/v1/datasets/{dataset_id}/split", json={"seed": 99})
    assert client.get(one).json()["out_of_date"] == [
        "The split changed since the recipe was saved."
    ]
    assert client.get(f"/api/v1/datasets/{dataset_id}/recipes/nope").status_code == 404
