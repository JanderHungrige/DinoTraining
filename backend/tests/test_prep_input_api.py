"""The input plan and "what the model sees" through the real ASGI app (doc 85)."""

from __future__ import annotations

import base64
import io
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def _dataset(client: TestClient, tmp_path: Path, side: int, images: int = 4) -> str:
    """Grey 1600x1200 frames, each with one `side` px box at (400, 300)."""
    dataset_id = str(client.post("/api/v1/datasets", json={"name": "Seen"}).json()["id"])
    for index in range(images):
        path = tmp_path / f"frame{index}.png"
        Image.new("RGB", (1600, 1200), (128, 128, 128)).save(path)
        box = {
            "label": "positive",
            "provenance": "hand-drawn",
            "prompt": "signal",
            "x": 400,
            "y": 300,
            "w": side,
            "h": side,
        }
        body = {"path": str(path), "width": 1600, "height": 1200, "boxes": [box]}
        assert client.put(f"/api/v1/datasets/{dataset_id}/images", json=body).status_code == 200
    return dataset_id


def _pixels(data_url: str) -> np.ndarray:
    raw = base64.b64decode(data_url.split(",", 1)[1])
    return np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"), dtype=np.int16)


def _preview(client: TestClient, dataset_id: str, target: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/datasets/{dataset_id}/input-preview", json={"target": target, "count": 1}
    )
    assert response.status_code == 200
    shown: dict[str, object] = response.json()["images"][0]
    assert (shown["objects"], shown["too_small"], shown["lost"]) == (1, 0, 0)
    return shown


def _coloured(pixel: np.ndarray) -> bool:
    return abs(int(pixel[0]) - int(pixel[2])) > 60


def test_a_letterboxed_preview_pads_and_puts_the_box_where_training_does(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id = _dataset(client, tmp_path, side=200)
    shown = _preview(client, dataset_id, "head-detection-dinov2")
    assert (shown["width"], shown["height"]) == (448, 448)
    pixels = _pixels(str(shown["data_url"]))
    # 1600x1200 → 448x336, padded by 56 px top and bottom (black).
    assert pixels[10, 224].max() < 20 and pixels[440, 224].max() < 20
    # Box left edge 400 * 0.28 = 112; top 300 * 0.28 + 56 = 140; 56 px tall.
    assert _coloured(pixels[170, 112]) and not _coloured(pixels[170, 100])


def test_a_stretched_preview_fills_the_square_and_scales_the_axes_apart(
    client: TestClient, tmp_path: Path
) -> None:
    # RF-DETR's processor resizes to exactly 384x384: no padding, x by 0.24, y by 0.32.
    dataset_id = _dataset(client, tmp_path, side=200)
    shown = _preview(client, dataset_id, "rf-detr-nano")
    assert (shown["width"], shown["height"]) == (384, 384)
    pixels = _pixels(str(shown["data_url"]))
    assert pixels[10, 192].min() > 100  # grey picture, not padding
    # Box: x 96..144, y 96..160 — taller than wide, as the stretch makes it.
    assert _coloured(pixels[150, 96]) and _coloured(pixels[150, 144])
    assert _coloured(pixels[160, 120]) and not _coloured(pixels[150, 120])


def test_small_objects_are_previewed_on_a_tile_and_marked(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id = _dataset(client, tmp_path, side=40)
    plan = client.get(
        f"/api/v1/datasets/{dataset_id}/input-plan", params={"target": "rf-detr-nano"}
    ).json()
    assert plan["tiling"]["recommended"] is True
    body = client.post(
        f"/api/v1/datasets/{dataset_id}/input-preview", json={"target": "rf-detr-nano"}
    ).json()
    shown = body["images"][0]
    assert shown["tile"] is not None
    x, y, w, h = shown["tile"]
    assert x <= 420 < x + w and y <= 320 < y + h  # the tile that holds the object

    untiled = client.post(
        f"/api/v1/datasets/{dataset_id}/input-preview",
        json={"target": "rf-detr-nano", "grid": 1},
    ).json()["images"][0]
    assert untiled["tile"] is None and untiled["too_small"] == 1


def test_a_missing_file_is_skipped_not_a_500(client: TestClient, tmp_path: Path) -> None:
    dataset_id = _dataset(client, tmp_path, side=200, images=2)
    (tmp_path / "frame0.png").unlink()
    body = client.post(
        f"/api/v1/datasets/{dataset_id}/input-preview", json={"target": "rf-detr-nano"}
    ).json()
    assert body["skipped"] == [str(tmp_path / "frame0.png")]
    assert len(body["images"]) == 1


def test_unknown_targets_and_datasets_are_refused(client: TestClient, tmp_path: Path) -> None:
    dataset_id = _dataset(client, tmp_path, side=200, images=1)
    assert (
        client.get(f"/api/v1/datasets/{dataset_id}/input-plan", params={"target": "x"}).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/datasets/nope/input-plan", params={"target": "rf-detr-nano"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/datasets/{dataset_id}/input-preview",
            json={"target": "rf-detr-nano", "grid": 99},
        ).status_code
        == 422
    )


def test_objects_in_other_tiles_are_not_counted_as_lost(client: TestClient, tmp_path: Path) -> None:
    # Found live on OSDaR23: a tile reported "lost 4 of 8", the four in the other tiles.
    dataset_id = _dataset(client, tmp_path, side=40, images=1)
    path = str(tmp_path / "frame0.png")
    far = {"label": "positive", "provenance": "hand-drawn", "prompt": "signal"}
    boxes = [
        far | {"x": 400, "y": 300, "w": 40, "h": 40},
        far | {"x": 1500, "y": 1100, "w": 60, "h": 60},
    ]
    body = {"path": path, "width": 1600, "height": 1200, "boxes": boxes}
    assert client.put(f"/api/v1/datasets/{dataset_id}/images", json=body).status_code == 200
    shown = client.post(
        f"/api/v1/datasets/{dataset_id}/input-preview", json={"target": "rf-detr-nano"}
    ).json()["images"][0]
    assert shown["tile"] is not None
    assert (shown["objects"], shown["lost"]) == (1, 0)


def test_a_whole_image_label_is_not_judged_by_its_boxes(client: TestClient, tmp_path: Path) -> None:
    # Found live on the chess set: "32 too small" for a classifier that learns no boxes.
    dataset_id = _dataset(client, tmp_path, side=4, images=1)
    shown = client.post(
        f"/api/v1/datasets/{dataset_id}/input-preview",
        json={"target": "head-classification-dinov2"},
    ).json()["images"][0]
    assert (shown["width"], shown["height"]) == (224, 224)
    assert shown["too_small"] == 0
