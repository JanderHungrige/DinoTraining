"""The default recipe for a model (doc 101), through the real ASGI app."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.main import create_app
from app.prep.default_recipe import profile_for
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


def _dataset(client: TestClient, tmp_path: Path, split: str | None = None) -> str:
    dataset_id = str(client.post("/api/v1/datasets", json={"name": "Default"}).json()["id"])
    for index in range(12):
        path = tmp_path / f"d{index}.png"
        Image.effect_noise((64, 48), 40 + index * 7).convert("RGB").save(path)
        box = {
            "label": "positive",
            "provenance": "hand-drawn",
            "prompt": "car" if index % 3 else "bus",
        }
        body: dict[str, Any] = {
            "path": str(path),
            "width": 64,
            "height": 48,
            "boxes": [box | {"x": 5, "y": 5, "w": 30, "h": 20}],
        }
        if split:
            body["split"] = split if index % 4 else "val"
        assert client.put(f"/api/v1/datasets/{dataset_id}/images", json=body).status_code == 200
    return dataset_id


def _run(client: TestClient, dataset_id: str, body: dict[str, Any]) -> dict[str, Any]:
    started = client.post(f"/api/v1/datasets/{dataset_id}/recipes/default", json=body)
    assert started.status_code == 202, started.text
    job_id = started.json()["job_id"]
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        job: dict[str, Any] = client.get(f"/api/v1/prep/default-recipes/{job_id}").json()
        if job["state"] in ("complete", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("default recipe did not finish")


class TestProfileFor:
    @pytest.mark.parametrize(
        ("model", "extra", "profile"),
        [
            (
                "head",
                {"head_type_id": "linear-classifier", "backbone_id": "dinov2-small"},
                "head-classification-dinov2",
            ),
            (
                "head",
                {"head_type_id": "linear-classifier", "backbone_id": "dinov3-vitb16"},
                "head-classification-dinov3",
            ),
            ("rf-detr-small", {}, "rf-detr-small"),
            ("sam2.1-hiera-large", {}, "sam2.1-hiera-large"),
            ("sam3", {}, "sam3"),
            ("dinov3-vitb16-segmentation", {}, "head-segmentation-dinov3"),
        ],
    )
    def test_every_trainable_model_has_one(
        self, model: str, extra: dict[str, str], profile: str
    ) -> None:
        assert profile_for(model, **extra) == profile

    def test_a_depth_head_has_none_and_says_why(self) -> None:
        with pytest.raises(ValueError, match="nothing to split"):
            profile_for("head", "dinov2-linear-depth-nyu", "dinov2-small")

    def test_resolve_route(self, client: TestClient) -> None:
        body = client.get("/api/v1/prep/targets/resolve", params={"model_id": "sam3"}).json()
        assert body == {"target": "sam3", "label": "Fine-tune SAM 3"}
        assert (
            client.get("/api/v1/prep/targets/resolve", params={"model_id": "nope"}).status_code
            == 422
        )


class TestDefaultRecipe:
    def test_from_nothing_to_a_recipe_in_one_call(self, client: TestClient, tmp_path: Path) -> None:
        """No audit, no split: the default does both, takes the recommendations, saves."""
        dataset_id = _dataset(client, tmp_path)
        job = _run(client, dataset_id, {"model_id": "rf-detr-nano"})
        assert job["state"] == "complete", job["message"]
        recipe = job["recipe"]
        assert recipe["name"] == "Default for RF-DETR (nano)"
        assert recipe["target"] == "rf-detr-nano"
        assert recipe["split"]["mode"] == "auto"
        listed = client.get(f"/api/v1/datasets/{dataset_id}/recipes").json()
        assert [r["recipe"]["id"] for r in listed] == [recipe["id"]]
        assert listed[0]["out_of_date"] == []

    def test_twice_returns_the_same_recipe(self, client: TestClient, tmp_path: Path) -> None:
        dataset_id = _dataset(client, tmp_path)
        first = _run(client, dataset_id, {"model_id": "sam3"})["recipe"]
        again = _run(client, dataset_id, {"model_id": "sam3"})
        assert again["recipe"]["id"] == first["id"]
        assert "already exists" in again["message"]

    def test_keeps_a_split_the_user_made(self, client: TestClient, tmp_path: Path) -> None:
        dataset_id = _dataset(client, tmp_path)
        made = client.post(
            f"/api/v1/datasets/{dataset_id}/split", json={"seed": 7, "val_fraction": 0.3}
        ).json()
        recipe = _run(client, dataset_id, {"model_id": "rf-detr-nano"})["recipe"]
        assert recipe["split"]["seed"] == 7
        assert recipe["split"]["sides"]["val"] == made["sides"]["val"]["images"]

    def test_keeps_a_split_that_came_with_the_data(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        dataset_id = _dataset(client, tmp_path, split="train")
        recipe = _run(client, dataset_id, {"model_id": "rf-detr-nano"})["recipe"]
        assert recipe["split"]["mode"] == "keep-source"

    def test_a_head_gets_its_task_and_backbone_profile(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        dataset_id = _dataset(client, tmp_path)
        body = {
            "model_id": "head",
            "head_type_id": "linear-classifier",
            "backbone_id": "dinov2-small",
        }
        recipe = _run(client, dataset_id, body)["recipe"]
        assert recipe["target"] == "head-classification-dinov2"
        assert recipe["name"] == "Default for Classification head on DINOv2"

    def test_refusals(self, client: TestClient, tmp_path: Path) -> None:
        assert (
            client.post(
                "/api/v1/datasets/nope/recipes/default", json={"model_id": "sam3"}
            ).status_code
            == 404
        )
        dataset_id = _dataset(client, tmp_path)
        bad = client.post(
            f"/api/v1/datasets/{dataset_id}/recipes/default", json={"model_id": "nope"}
        )
        assert bad.status_code == 422
        assert client.get("/api/v1/prep/default-recipes/nope").status_code == 404

    def test_an_empty_dataset_fails_with_the_reason(self, client: TestClient) -> None:
        dataset_id = str(client.post("/api/v1/datasets", json={"name": "Empty"}).json()["id"])
        job = _run(client, dataset_id, {"model_id": "rf-detr-nano"})
        assert job["state"] == "failed"
        assert "no images" in job["message"].lower()
