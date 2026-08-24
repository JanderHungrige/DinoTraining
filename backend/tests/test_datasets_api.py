"""Tests for the dataset endpoints, exercised through the real ASGI app."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from tests.datasets_api_testkit import dataset_client, make_dataset


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


def annotation(*labels: str, path: str = "/images/a.jpg") -> dict[str, Any]:
    return {
        "path": path,
        "width": 200,
        "height": 200,
        "boxes": [
            {
                "label": label,
                "provenance": "grounding-dino",
                "x": 10,
                "y": 10,
                "w": 20,
                "h": 20,
            }
            for label in labels
        ],
    }


class TestCreateAndList:
    async def test_create_returns_201_with_an_id(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        assert len(dataset["id"]) == 32
        assert dataset["counts"]["images"] == 0

    async def test_blank_name_is_rejected(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/datasets", json={"name": ""})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    async def test_list_returns_created_datasets(self, client: AsyncClient) -> None:
        await make_dataset(client, name="A")
        await make_dataset(client, name="B")
        body = (await client.get("/api/v1/datasets")).json()
        assert {d["name"] for d in body["datasets"]} == {"A", "B"}

    async def test_get_unknown_is_404(self, client: AsyncClient) -> None:
        assert (await client.get("/api/v1/datasets/nope")).status_code == 404

    async def test_delete_unknown_is_404(self, client: AsyncClient) -> None:
        assert (await client.delete("/api/v1/datasets/nope")).status_code == 404


class TestAnnotations:
    async def test_put_records_boxes_and_returns_counts(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        response = await client.put(
            f"/api/v1/datasets/{dataset['id']}/images",
            json=annotation("positive", "negative", "unclear"),
        )

        assert response.status_code == 200
        counts = response.json()
        assert counts == {
            "images": 1,
            "boxes": 3,
            # Wave 4 added masks to the counter payload. Boxes and masks are separate
            # tallies; the verdict counters below span both.
            "masks": 0,
            "positive": 1,
            "negative": 1,
            "unclear": 1,
        }

    async def test_put_is_idempotent(self, client: AsyncClient) -> None:
        """Saving the same image twice must not double its boxes."""
        dataset = await make_dataset(client)
        payload = annotation("positive", "positive")
        await client.put(f"/api/v1/datasets/{dataset['id']}/images", json=payload)
        counts = (
            await client.put(f"/api/v1/datasets/{dataset['id']}/images", json=payload)
        ).json()

        assert counts["images"] == 1
        assert counts["boxes"] == 2

    async def test_put_to_unknown_dataset_is_404(self, client: AsyncClient) -> None:
        response = await client.put("/api/v1/datasets/nope/images", json=annotation("positive"))
        assert response.status_code == 404

    async def test_out_of_frame_box_is_422(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        payload = annotation("positive")
        payload["boxes"][0]["x"] = 190
        payload["boxes"][0]["w"] = 50

        response = await client.put(f"/api/v1/datasets/{dataset['id']}/images", json=payload)
        assert response.status_code == 422

    async def test_zero_area_box_is_422(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        payload = annotation("positive")
        payload["boxes"][0]["w"] = 0

        response = await client.put(f"/api/v1/datasets/{dataset['id']}/images", json=payload)
        assert response.status_code == 422

    async def test_invalid_label_is_422(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        payload = annotation("positive")
        payload["boxes"][0]["label"] = "maybe"

        response = await client.put(f"/api/v1/datasets/{dataset['id']}/images", json=payload)
        assert response.status_code == 422

    async def test_counts_endpoint_matches_the_put_response(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        put_counts = (
            await client.put(
                f"/api/v1/datasets/{dataset['id']}/images", json=annotation("positive")
            )
        ).json()
        get_counts = (await client.get(f"/api/v1/datasets/{dataset['id']}/counts")).json()

        assert put_counts == get_counts

    async def test_counts_appear_in_the_list_response(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        await client.put(f"/api/v1/datasets/{dataset['id']}/images", json=annotation("positive"))

        listed = (await client.get("/api/v1/datasets")).json()["datasets"][0]
        assert listed["counts"]["positive"] == 1


class TestExport:
    async def test_writes_a_coco_file(self, client: AsyncClient, tmp_path: Path) -> None:
        dataset = await make_dataset(client, prompt="a cat")
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images",
            json=annotation("positive", "negative"),
        )

        response = await client.post(f"/api/v1/datasets/{dataset['id']}/export/coco")
        assert response.status_code == 200

        body = response.json()
        assert body["images"] == 1
        assert body["annotations"] == 1  # the negative is excluded

        written = json.loads(Path(body["path"]).read_text())
        assert written["info"]["prompt"] == "a cat"
        assert written["annotations"][0]["bbox"] == [10, 10, 20, 20]

    async def test_export_of_unknown_dataset_is_404(self, client: AsyncClient) -> None:
        assert (await client.post("/api/v1/datasets/nope/export/coco")).status_code == 404

    async def test_export_with_no_annotations_still_writes(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        body = (await client.post(f"/api/v1/datasets/{dataset['id']}/export/coco")).json()
        assert body["annotations"] == 0
        assert Path(body["path"]).is_file()


class TestDelete:
    async def test_delete_removes_the_dataset(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        await client.put(f"/api/v1/datasets/{dataset['id']}/images", json=annotation("positive"))

        assert (await client.delete(f"/api/v1/datasets/{dataset['id']}")).status_code == 200
        assert (await client.get(f"/api/v1/datasets/{dataset['id']}")).status_code == 404
        assert (await client.get("/api/v1/datasets")).json()["datasets"] == []
