"""Tests for GET /api/v1/inference/source — what the user pointed the viewer at."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.inference_api_testkit import stub_inference_client, write_image

SOURCE = "/api/v1/inference/source"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    yield from stub_inference_client(tmp_path, monkeypatch)


class TestSourceListing:
    def test_a_single_image_is_one_item(self, client: TestClient, tmp_path: Path) -> None:
        image_path = write_image(tmp_path / "one.png")

        response = client.get(SOURCE, params={"path": image_path})
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

        payload = client.get(SOURCE, params={"path": str(folder)}).json()

        assert payload["kind"] == "folder"
        assert [item["name"] for item in payload["items"]] == ["a.png", "b.png"]
        assert payload["truncated"] is False

    def test_an_empty_folder_is_200_with_no_items(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        # A routine discovery, not a failure — the viewer has to be able to say it.
        empty = tmp_path / "empty"
        empty.mkdir()

        response = client.get(SOURCE, params={"path": str(empty)})

        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_item_ids_are_opaque_and_unique(self, client: TestClient, tmp_path: Path) -> None:
        folder = tmp_path / "ids"
        folder.mkdir()
        write_image(folder / "a.png")
        write_image(folder / "b.png")

        items = client.get(SOURCE, params={"path": str(folder)}).json()["items"]

        assert len({item["item_id"] for item in items}) == 2
        assert all("/" not in item["item_id"] for item in items)

    def test_a_missing_path_is_404(self, client: TestClient, tmp_path: Path) -> None:
        response = client.get(SOURCE, params={"path": str(tmp_path / "gone")})

        assert response.status_code == 404
        # Names the path, so this cannot be satisfied by FastAPI's own "no such route".
        assert "gone" in response.json()["error"]["message"]

    def test_a_non_image_file_is_415(self, client: TestClient, tmp_path: Path) -> None:
        notes = tmp_path / "notes.txt"
        notes.write_text("not a picture")

        response = client.get(SOURCE, params={"path": str(notes)})
        assert response.status_code == 415

    def test_an_empty_path_is_422(self, client: TestClient) -> None:
        assert client.get(SOURCE, params={"path": ""}).status_code == 422
