"""The split through the API: stored, kept, and refused with a reason (doc 84)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.datasets.db import transaction
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def _dataset(client: TestClient, frames: int, split: str | None = None) -> str:
    dataset_id = str(client.post("/api/v1/datasets", json={"name": "Ride"}).json()["id"])
    for i in range(frames):
        body: dict[str, object] = {
            "path": f"/frames/{i:04d}.jpg",
            "width": 100,
            "height": 100,
            "boxes": [
                {
                    "label": "positive",
                    "provenance": "hand-drawn",
                    "prompt": "signal",
                    "x": 1,
                    "y": 1,
                    "w": 5,
                    "h": 5,
                }
            ],
            "frame": {"sequence": "/v/ride.mp4", "frame_index": i},
        }
        if split:
            body["split"] = split
        client.put(f"/api/v1/datasets/{dataset_id}/images", json=body)
    return dataset_id


def test_a_split_is_stored_and_reported(client: TestClient) -> None:
    dataset_id = _dataset(client, 200)
    report = client.post(f"/api/v1/datasets/{dataset_id}/split", json={}).json()
    assert report["sides"]["train"]["images"] > report["sides"]["val"]["images"] > 0
    assert report["buffer"] > 0
    with transaction() as connection:
        stored = {row[0] for row in connection.execute("SELECT DISTINCT split FROM images")}
    assert stored == {"train", "val", "test", "buffer"}
    again = client.get(f"/api/v1/datasets/{dataset_id}/split").json()
    assert again["sides"] == report["sides"]
    # No audit yet, so scenes could not be grouped: the user is told, not left guessing.
    assert "not been audited" in report["warnings"][0]


def test_keeping_a_source_split_needs_every_image_to_have_one(client: TestClient) -> None:
    dataset_id = _dataset(client, 10)
    response = client.post(f"/api/v1/datasets/{dataset_id}/split", json={"mode": "keep-source"})
    assert response.status_code == 422
    assert "came with a split" in response.text


def test_a_kept_source_split_is_reported_as_it_is(client: TestClient) -> None:
    dataset_id = _dataset(client, 6, split="train")
    report = client.post(
        f"/api/v1/datasets/{dataset_id}/split", json={"mode": "keep-source"}
    ).json()
    assert report["sides"]["train"]["images"] == 6


def test_impossible_shares_are_refused(client: TestClient) -> None:
    dataset_id = _dataset(client, 5)
    body = {"val_fraction": 0.6, "test_fraction": 0.5}
    assert client.post(f"/api/v1/datasets/{dataset_id}/split", json=body).status_code == 422


def test_an_unsplit_dataset_has_no_split(client: TestClient) -> None:
    dataset_id = _dataset(client, 3)
    assert client.get(f"/api/v1/datasets/{dataset_id}/split").status_code == 404
