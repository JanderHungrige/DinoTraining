"""Annotation quality aids (doc 109): guideline and second look through the API."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.datasets_api_testkit import dataset_client, make_dataset


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


async def _annotated(client: AsyncClient, count: int) -> str:
    dataset = await make_dataset(client)
    for i in range(count):
        box = {
            "label": "positive",
            "provenance": "hand-drawn",
            "prompt": "ring",
            "x": 1,
            "y": 1,
            "w": 2,
            "h": 2,
        }
        body = {"path": f"/images/{i}.jpg", "width": 10, "height": 10, "boxes": [box]}
        assert (
            await client.put(f"/api/v1/datasets/{dataset['id']}/images", json=body)
        ).status_code == 200
    return str(dataset["id"])


class TestGuideline:
    async def test_empty_until_written_then_exported_with_the_annotations(
        self, client: AsyncClient
    ) -> None:
        dataset_id = await _annotated(client, 1)
        url = f"/api/v1/datasets/{dataset_id}/guideline"
        assert (await client.get(url)).json() == {"text": ""}
        text = "Rings: outline with the hole filled.\nOccluded more than half: unclear."
        assert (await client.put(url, json={"text": text})).json() == {"text": text}
        written = (await client.post(f"/api/v1/datasets/{dataset_id}/export/coco")).json()["path"]
        coco = json.loads(Path(written).read_text())
        assert coco["info"]["guideline"] == text
        assert (Path(written).parent / "guideline.md").read_text() == text

    async def test_a_novel_is_refused(self, client: AsyncClient) -> None:
        dataset_id = await _annotated(client, 1)
        refused = await client.put(
            f"/api/v1/datasets/{dataset_id}/guideline", json={"text": "x" * 20_001}
        )
        assert refused.status_code == 422


class TestSecondLook:
    async def test_a_sample_its_verdicts_and_the_rate(self, client: AsyncClient) -> None:
        dataset_id = await _annotated(client, 12)
        base = f"/api/v1/datasets/{dataset_id}/second-look"
        drawn = (await client.post(base, json={"share": 0.05})).json()
        assert len(drawn["sample"]) == 5  # 5 % of 12 rounds to 1; the floor is five
        assert drawn["rate"] is None
        first, second = drawn["sample"][:2]
        await client.put(f"{base}/verdict", json={"path": first, "verdict": "right"})
        look = (
            await client.put(f"{base}/verdict", json={"path": second, "verdict": "changed"})
        ).json()
        assert (look["reviewed"], look["changed"], look["rate"]) == (2, 1, 0.5)
        assert (await client.get(base)).json()["reviewed"] == 2

    async def test_refusals(self, client: AsyncClient) -> None:
        empty = (await make_dataset(client))["id"]
        assert (
            await client.post(f"/api/v1/datasets/{empty}/second-look", json={})
        ).status_code == 422
        assert (await client.get(f"/api/v1/datasets/{empty}/second-look")).status_code == 404
        dataset_id = await _annotated(client, 6)
        base = f"/api/v1/datasets/{dataset_id}/second-look"
        await client.post(base, json={})
        outside = await client.put(
            f"{base}/verdict", json={"path": "/nope.jpg", "verdict": "right"}
        )
        assert outside.status_code == 422
