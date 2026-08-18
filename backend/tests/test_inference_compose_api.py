"""Tests for POST /api/v1/inference/compose — N heads over one image.

`passes` is the assertion that matters. "Three heads returned three predictions" passes
just as well when the feature does nothing at all.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.inference_api_testkit import (
    add_classifier,
    add_segmenter,
    stub_inference_client,
    write_image,
)

COMPOSE = "/api/v1/inference/compose"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    yield from stub_inference_client(tmp_path, monkeypatch)


def request_body(image_path: str, instance_ids: list[str], **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "image_path": image_path,
        "backbone_id": "dinov2-small",
        "instance_ids": instance_ids,
    }
    payload.update(extra)
    return payload


class TestSuccess:
    def test_heads_sharing_a_framing_share_a_pass(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        first = add_classifier(3, "A")
        second = add_classifier(4, "B")
        image_path = write_image(tmp_path / "shape.png")

        response = client.post(COMPOSE, json=request_body(image_path, [first, second]))
        assert response.status_code == 200, response.text

        payload = response.json()
        assert [p["instance_id"] for p in payload["predictions"]] == [first, second]
        assert payload["passes"] == 1  # both are center-crop @ 224
        assert payload["elapsed_ms"] >= 0

    def test_a_second_framing_costs_a_second_pass(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        classifier = add_classifier()
        segmenter = add_segmenter()
        image_path = write_image(tmp_path / "shape.png")

        payload = client.post(
            COMPOSE, json=request_body(image_path, [classifier, segmenter])
        ).json()

        assert payload["passes"] == 2
        assert [p["render_hint"] for p in payload["predictions"]] == ["labels", "masks"]

    def test_predictions_keep_the_requested_order(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Grouping reorders the work; the response must not reorder the answers."""
        classifier = add_classifier(3, "A")
        segmenter = add_segmenter(3, "B")
        image_path = write_image(tmp_path / "shape.png")

        payload = client.post(
            COMPOSE, json=request_body(image_path, [segmenter, classifier])
        ).json()

        assert [p["head_name"] for p in payload["predictions"]] == ["B", "A"]

    def test_duplicate_ids_are_collapsed(self, client: TestClient, tmp_path: Path) -> None:
        classifier = add_classifier()
        image_path = write_image(tmp_path / "shape.png")

        payload = client.post(
            COMPOSE, json=request_body(image_path, [classifier, classifier])
        ).json()

        assert len(payload["predictions"]) == 1


class TestFailures:
    def test_an_empty_head_list_is_422(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post(
            COMPOSE, json=request_body(write_image(tmp_path / "shape.png"), [])
        )
        assert response.status_code == 422

    def test_an_unknown_head_is_404_and_names_it(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        response = client.post(
            COMPOSE,
            json=request_body(write_image(tmp_path / "shape.png"), [add_classifier(), "nope"]),
        )

        assert response.status_code == 404
        message = response.json()["error"]["message"]
        # Names *only* the offending id: listing every head in the request would leave
        # the user guessing which one to fix.
        assert "nope" in message
        assert message.count(",") == 0

    def test_a_non_image_file_is_415(self, client: TestClient, tmp_path: Path) -> None:
        notes = tmp_path / "notes.txt"
        notes.write_text("not a picture")

        response = client.post(COMPOSE, json=request_body(str(notes), [add_classifier()]))
        assert response.status_code == 415

    def test_a_mismatched_backbone_is_409(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post(
            COMPOSE,
            json=request_body(
                write_image(tmp_path / "shape.png"),
                [add_classifier()],
                backbone_id="dinov2-base",
            ),
        )

        assert response.status_code == 409
        assert "dinov2-small" in response.json()["error"]["message"]
