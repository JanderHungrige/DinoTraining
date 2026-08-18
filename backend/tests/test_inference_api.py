"""Tests for POST /api/v1/inference — one head, one image.

The status codes are the contract the viewer branches on, and each maps to a different
fix: 404 pick another head, 409 install or switch backbone, 415 that file is not an
image. A blanket 400 would collapse three different remedies into one dead end.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.inference_api_testkit import add_classifier, stub_inference_client, write_image

ENDPOINT = "/api/v1/inference"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    yield from stub_inference_client(tmp_path, monkeypatch)


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
