"""Augmentation presets and preview through the real ASGI app (doc 87)."""

from __future__ import annotations

import base64
import io
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.core.config import get_settings
from app.main import create_app
from app.prep.augment_plan import recommend


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def _dataset(client: TestClient, tmp_path: Path, prompt: str) -> str:
    """One 400x300 grey picture with a red 80x60 object at (40, 50)."""
    dataset_id = str(client.post("/api/v1/datasets", json={"name": "Aug"}).json()["id"])
    path = tmp_path / "a.png"
    image = Image.new("RGB", (400, 300), (128, 128, 128))
    ImageDraw.Draw(image).rectangle((40, 50, 119, 109), fill=(220, 30, 30))
    image.save(path)
    box = {"label": "positive", "provenance": "hand-drawn", "prompt": prompt}
    body = {
        "path": str(path),
        "width": 400,
        "height": 300,
        "boxes": [box | {"x": 40, "y": 50, "w": 80, "h": 60}],
    }
    assert client.put(f"/api/v1/datasets/{dataset_id}/images", json=body).status_code == 200
    return dataset_id


def test_the_domain_is_guessed_from_class_names_and_says_so() -> None:
    assert recommend(["platelets", "rbc"])[0] == "microscopy"
    assert recommend(["signal", "person"])[0] == "outdoor"
    preset, reason = recommend(["widget"])
    assert preset == "general" and "do not suggest" in reason


def test_a_side_dependent_class_turns_mirroring_off_everywhere(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id = _dataset(client, tmp_path, "left arrow")
    plan = client.get(
        f"/api/v1/datasets/{dataset_id}/augmentation", params={"target": "head-detection-dinov2"}
    ).json()
    assert plan["guarded_classes"] == ["left arrow"]
    assert "Mirroring is left out" in plan["reason"]
    guarded = {p["id"]: p["guarded"] for p in plan["presets"]}
    assert guarded["general"] and guarded["microscopy"] and not guarded["outdoor"]


def test_the_preview_shows_the_original_then_versions_with_boxes_on_the_object(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id = _dataset(client, tmp_path, "cell")
    response = client.post(
        f"/api/v1/datasets/{dataset_id}/augmentation-preview",
        json={"target": "head-detection-dinov2", "preset": "microscopy", "count": 3},
    )
    assert response.status_code == 200
    images = response.json()["images"]
    assert len(images) == 4 and all(i["lost"] == 0 for i in images)
    for shown in images:
        raw = base64.b64decode(shown["data_url"].split(",", 1)[1])
        pixels = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"), dtype=np.int16)
        reddish = (pixels[..., 0] - pixels[..., 2]) > 60
        assert reddish.sum() > 300  # the object survived every version


def test_an_unknown_preset_is_a_422_with_the_reason(client: TestClient, tmp_path: Path) -> None:
    dataset_id = _dataset(client, tmp_path, "cell")
    response = client.post(
        f"/api/v1/datasets/{dataset_id}/augmentation-preview",
        json={"target": "head-detection-dinov2", "preset": "sepia"},
    )
    assert response.status_code == 422 and "sepia" in str(response.json()["error"])
