"""Tests for POST /api/v1/inference.

The status codes are the contract the viewer branches on, and each maps to a different
fix: 404 pick another head, 409 install or switch backbone, 415 that file is not an
image. A blanket 400 would collapse three different remedies into one dead end.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.main import create_app
from app.ml.heads.store import HeadInstanceStore
from tests.head_testkit import install_fake_backbone

EMBED = 32
ENDPOINT = "/api/v1/inference"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_connection()

    from app.ml.backbone import BackboneCapabilities, BackboneFeatures

    install_fake_backbone(get_settings(), "dinov2-small", EMBED)
    capabilities = BackboneCapabilities(
        model_id="dinov2-small",
        family="dinov2",
        patch_size=14,
        embed_dim=EMBED,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )

    class StubBackbone:
        def __init__(self) -> None:
            self.capabilities = capabilities
            self.device = "cpu"

    def fake_extract(backbone: object, pixel_values: torch.Tensor) -> BackboneFeatures:
        rows = int(pixel_values.shape[-2]) // 14
        cols = int(pixel_values.shape[-1]) // 14
        return BackboneFeatures(
            cls=torch.randn(1, EMBED),
            patches=torch.randn(1, EMBED, rows, cols),
            grid=(rows, cols),
        )

    monkeypatch.setattr("app.ml.inference.engine.load_backbone", lambda *a, **k: StubBackbone())
    monkeypatch.setattr("app.ml.inference.engine.extract", fake_extract)

    with TestClient(create_app()) as test_client:
        yield test_client
    reset_connection()
    get_settings.cache_clear()


def add_classifier(num_classes: int = 3) -> str:
    instance = HeadInstanceStore().register(
        name="Shapes classifier",
        kind="trained-here",
        head_type_id="linear-classifier",
        task="classification",
        backbone_id="dinov2-small",
        backbone_family="dinov2",
        embed_dim=EMBED,
        num_classes=num_classes,
        weights={
            "linear.weight": torch.randn(num_classes, EMBED),
            "linear.bias": torch.randn(num_classes),
        },
        class_names=tuple(f"class{i}" for i in range(num_classes)),
    )
    return instance.id


def write_image(path: Path, size: tuple[int, int] = (320, 240)) -> str:
    Image.new("RGB", size, (120, 90, 60)).save(path)
    return str(path)


def body(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "image_path": "",
        "backbone_id": "dinov2-small",
        "instance_id": "",
    }
    payload.update(overrides)
    return payload


class TestSuccess:
    def test_returns_a_prediction(self, client: TestClient, tmp_path: Path) -> None:
        instance_id = add_classifier()
        image_path = write_image(tmp_path / "shape.png")

        response = client.post(
            ENDPOINT, json=body(image_path=image_path, instance_id=instance_id)
        )
        assert response.status_code == 200, response.text

        payload = response.json()
        assert payload["render_hint"] == "labels"
        assert payload["task"] == "classification"
        assert len(payload["payload"]["scores"]) == 3
        assert payload["class_names"] == ["class0", "class1", "class2"]

    def test_response_names_the_head_rather_than_a_file(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Doc 12's cross-tab contract reaches the API surface."""
        instance_id = add_classifier()
        image_path = write_image(tmp_path / "shape.png")

        payload = client.post(
            ENDPOINT, json=body(image_path=image_path, instance_id=instance_id)
        ).json()
        assert payload["head_name"] == "Shapes classifier"
        assert ".safetensors" not in payload["head_name"]

    def test_grid_and_timing_are_reported(self, client: TestClient, tmp_path: Path) -> None:
        instance_id = add_classifier()
        image_path = write_image(tmp_path / "shape.png")
        payload = client.post(
            ENDPOINT, json=body(image_path=image_path, instance_id=instance_id)
        ).json()
        assert payload["grid"][0] > 0
        assert payload["elapsed_ms"] >= 0


class TestFailures:
    def test_unknown_head_is_404(self, client: TestClient, tmp_path: Path) -> None:
        image_path = write_image(tmp_path / "shape.png")
        response = client.post(ENDPOINT, json=body(image_path=image_path, instance_id="nope"))
        assert response.status_code == 404

    def test_missing_file_is_404(self, client: TestClient, tmp_path: Path) -> None:
        instance_id = add_classifier()
        response = client.post(
            ENDPOINT,
            json=body(image_path=str(tmp_path / "absent.png"), instance_id=instance_id),
        )
        assert response.status_code == 404

    def test_a_non_image_file_is_415(self, client: TestClient, tmp_path: Path) -> None:
        instance_id = add_classifier()
        not_an_image = tmp_path / "notes.txt"
        not_an_image.write_text("this is not a picture")

        response = client.post(
            ENDPOINT, json=body(image_path=str(not_an_image), instance_id=instance_id)
        )
        assert response.status_code == 415

    def test_wrong_backbone_is_409_and_names_the_right_one(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        instance_id = add_classifier()
        image_path = write_image(tmp_path / "shape.png")

        response = client.post(
            ENDPOINT,
            json=body(
                image_path=image_path, instance_id=instance_id, backbone_id="dinov2-base"
            ),
        )
        assert response.status_code == 409
        assert "dinov2-small" in response.json()["error"]["message"]

    def test_out_of_range_threshold_is_422(self, client: TestClient, tmp_path: Path) -> None:
        instance_id = add_classifier()
        image_path = write_image(tmp_path / "shape.png")
        response = client.post(
            ENDPOINT,
            json=body(
                image_path=image_path, instance_id=instance_id, score_threshold=5.0
            ),
        )
        assert response.status_code == 422

    def test_missing_fields_are_422(self, client: TestClient) -> None:
        assert client.post(ENDPOINT, json={"image_path": "/tmp/x.png"}).status_code == 422


class TestSourceListing:
    """`GET /inference/source` — what the user pointed the viewer at."""

    SOURCE = "/api/v1/inference/source"

    def test_a_single_image_is_one_item(self, client: TestClient, tmp_path: Path) -> None:
        image_path = write_image(tmp_path / "one.png")

        response = client.get(self.SOURCE, params={"path": image_path})
        assert response.status_code == 200, response.text

        payload = response.json()
        assert payload["kind"] == "file"
        assert len(payload["items"]) == 1
        assert payload["items"][0]["name"] == "one.png"
        assert payload["items"][0]["path"] == image_path

    def test_a_folder_lists_its_images(self, client: TestClient, tmp_path: Path) -> None:
        folder = tmp_path / "shots"
        folder.mkdir()
        write_image(folder / "b.png")
        write_image(folder / "a.png")
        (folder / "notes.txt").write_text("ignored")

        payload = client.get(self.SOURCE, params={"path": str(folder)}).json()

        assert payload["kind"] == "folder"
        assert [item["name"] for item in payload["items"]] == ["a.png", "b.png"]
        assert payload["truncated"] is False

    def test_an_empty_folder_is_200_with_no_items(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        # A routine discovery, not a failure — the viewer has to be able to say it.
        empty = tmp_path / "empty"
        empty.mkdir()

        response = client.get(self.SOURCE, params={"path": str(empty)})

        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_item_ids_are_opaque_and_unique(self, client: TestClient, tmp_path: Path) -> None:
        folder = tmp_path / "ids"
        folder.mkdir()
        write_image(folder / "a.png")
        write_image(folder / "b.png")

        items = client.get(self.SOURCE, params={"path": str(folder)}).json()["items"]

        assert len({item["item_id"] for item in items}) == 2
        assert all("/" not in item["item_id"] for item in items)

    def test_a_missing_path_is_404(self, client: TestClient, tmp_path: Path) -> None:
        response = client.get(self.SOURCE, params={"path": str(tmp_path / "gone")})

        assert response.status_code == 404
        # Names the path, so this cannot be satisfied by FastAPI's own "no such route".
        assert "gone" in response.json()["error"]["message"]

    def test_a_non_image_file_is_415(self, client: TestClient, tmp_path: Path) -> None:
        notes = tmp_path / "notes.txt"
        notes.write_text("not a picture")

        response = client.get(self.SOURCE, params={"path": str(notes)})
        assert response.status_code == 415

    def test_an_empty_path_is_422(self, client: TestClient) -> None:
        assert client.get(self.SOURCE, params={"path": ""}).status_code == 422
