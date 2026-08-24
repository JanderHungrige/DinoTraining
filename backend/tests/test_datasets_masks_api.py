"""Tests for the mask endpoints on the dataset API, through the real ASGI app.

Split out of test_datasets_api.py when that file hit the 300-line limit; masks are their
own concern with their own encoding rules.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.datasets_api_testkit import dataset_client, make_dataset, mask_payload


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


class TestMaskAnnotations:
    async def test_put_records_masks_and_returns_counts(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        response = await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks",
            json=mask_payload("positive", "negative"),
        )

        assert response.status_code == 200
        assert response.json() == {
            "images": 1,
            "boxes": 0,
            "masks": 2,
            "positive": 1,
            "negative": 1,
            "unclear": 0,
        }

    async def test_put_to_an_unknown_dataset_is_404(self, client: AsyncClient) -> None:
        response = await client.put(
            "/api/v1/datasets/nope/images/masks", json=mask_payload("positive")
        )
        assert response.status_code == 404

    async def test_a_mask_sized_wrong_for_its_image_is_422_not_500(
        self, client: AsyncClient
    ) -> None:
        dataset = await make_dataset(client)
        payload = mask_payload("positive")
        payload["width"] = 8  # the RLE still describes a 4x4 frame
        response = await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks", json=payload
        )
        assert response.status_code == 422

    async def test_an_empty_mask_is_422_not_500(self, client: AsyncClient) -> None:
        """Reaches the ValueError backstop in the handler, not Pydantic."""
        dataset = await make_dataset(client)
        payload = mask_payload("positive")
        payload["masks"][0]["rle"]["counts"] = [16]  # all background
        response = await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks", json=payload
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "validation_error"
        # The reason must reach the caller, not just the log.
        assert "foreground" in body["error"]["message"]

    async def test_a_hostile_run_length_is_rejected_by_arithmetic(
        self, client: AsyncClient
    ) -> None:
        """A huge run must be refused by summing the list, never by allocating a mask."""
        dataset = await make_dataset(client)
        payload = mask_payload("positive")
        payload["masks"][0]["rle"]["counts"] = [10_000_000_000]
        response = await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks", json=payload
        )
        assert response.status_code == 422


class TestCocoWithMasks:
    async def test_export_includes_segmentation_for_positive_masks(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks",
            json=mask_payload("positive", "negative"),
        )

        response = await client.post(f"/api/v1/datasets/{dataset['id']}/export/coco")
        assert response.status_code == 200

        coco = json.loads(Path(response.json()["path"]).read_text())
        segmentations = [a for a in coco["annotations"] if "segmentation" in a]
        assert len(segmentations) == 1, "negative masks must not be exported"
        assert segmentations[0]["segmentation"]["size"] == [4, 4]
        assert segmentations[0]["bbox"] == [1.0, 1.0, 2.0, 2.0]
        assert segmentations[0]["area"] == 4
