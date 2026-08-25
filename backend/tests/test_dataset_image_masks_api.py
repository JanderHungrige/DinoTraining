"""Reading one image's stored masks back (doc 61).

This route is what makes storing masks in the Studio safe rather than destructive. Saving
replaces an image's whole mask set, so a Studio that could not load them would wipe every
mask on the first save of an image someone had already segmented. The tests that matter
here are the round trip and the two "empty is not an error" cases.
"""

from __future__ import annotations

import base64
import io
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from httpx import AsyncClient
from PIL import Image

from tests.datasets_api_testkit import dataset_client, make_dataset

WIDTH, HEIGHT = 8, 6


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


@pytest.fixture
def image_path(tmp_path: Path) -> str:
    path = tmp_path / "pics" / "a.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (WIDTH, HEIGHT), "grey").save(path)
    return str(path)


def counts_for(box: tuple[int, int, int, int]) -> list[int]:
    """Column-major run lengths for a filled rectangle, starting with background."""
    from app.datasets.rle import rle_encode

    x, y, w, h = box
    array = np.zeros((HEIGHT, WIDTH), dtype=bool)
    array[y : y + h, x : x + w] = True
    return rle_encode(array)[0]


def mask_payload(
    image_path: str, *, box: tuple[int, int, int, int] = (2, 1, 3, 2), **over: Any
) -> dict[str, Any]:
    return {
        "path": image_path,
        "width": WIDTH,
        "height": HEIGHT,
        "masks": [
            {
                "label": "positive",
                "provenance": "grounded-sam",
                "rle": {"size": [HEIGHT, WIDTH], "counts": counts_for(box)},
                "prompt": "sky",
                "score": 0.82,
                **over,
            }
        ],
    }


async def stored_path(client: AsyncClient, dataset_id: str) -> str:
    body = (await client.get(f"/api/v1/datasets/{dataset_id}/images")).json()
    path: str = body["images"][0]["path"]
    return path


async def read_masks(client: AsyncClient, dataset_id: str, path: str) -> dict[str, Any]:
    response = await client.get(
        f"/api/v1/datasets/{dataset_id}/images/masks", params={"path": path}
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


class TestTheRoundTrip:
    async def test_a_saved_mask_comes_back(self, client: AsyncClient, image_path: str) -> None:
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks", json=mask_payload(image_path)
        )
        path = await stored_path(client, dataset["id"])

        body = await read_masks(client, dataset["id"], path)

        assert len(body["masks"]) == 1
        assert body["masks"][0]["prompt"] == "sky"
        assert body["masks"][0]["label"] == "positive"
        assert body["masks"][0]["provenance"] == "grounded-sam"

    async def test_the_rle_survives_unchanged(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # It is what gets stored and what gets exported; a round trip that altered it
        # would change the segmentation without anyone editing anything.
        dataset = await make_dataset(client)
        sent = mask_payload(image_path)
        await client.put(f"/api/v1/datasets/{dataset['id']}/images/masks", json=sent)
        path = await stored_path(client, dataset["id"])

        body = await read_masks(client, dataset["id"], path)

        assert body["masks"][0]["rle"] == sent["masks"][0]["rle"]

    async def test_it_reports_the_box_derived_from_the_mask(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # The hit target. Mask pixels cannot be focused; this rect is what the review
        # surface turns into a button.
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks",
            json=mask_payload(image_path, box=(2, 1, 3, 2)),
        )
        path = await stored_path(client, dataset["id"])

        mask = (await read_masks(client, dataset["id"], path))["masks"][0]

        assert (mask["x"], mask["y"], mask["w"], mask["h"]) == (2.0, 1.0, 3.0, 2.0)

    async def test_the_preview_matches_the_stored_rle(
        self, client: AsyncClient, image_path: str
    ) -> None:
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks",
            json=mask_payload(image_path, box=(2, 1, 3, 2)),
        )
        path = await stored_path(client, dataset["id"])

        mask = (await read_masks(client, dataset["id"], path))["masks"][0]
        pixels = np.array(Image.open(io.BytesIO(base64.b64decode(mask["mask_png"]))))

        assert pixels.shape == (HEIGHT, WIDTH)
        assert set(np.unique(pixels).tolist()) == {0, 255}
        ys, xs = (pixels > 0).nonzero()
        assert (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) == (2, 1, 4, 2)

    async def test_it_keeps_the_producer_snapshot(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # A snapshot outlives the model that made it — the whole point of doc 29.
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks",
            json=mask_payload(
                image_path,
                producer={"id": "grounded-sam", "label": "Grounded SAM", "concept": "sky"},
            ),
        )
        path = await stored_path(client, dataset["id"])

        mask = (await read_masks(client, dataset["id"], path))["masks"][0]

        assert mask["producer"]["id"] == "grounded-sam"
        assert mask["producer"]["concept"] == "sky"


class TestEmptyIsNotAnError:
    async def test_an_image_with_no_masks_is_an_empty_list(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # The ordinary case. A 404 here would make every un-segmented image look broken.
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images",
            json={
                "path": image_path,
                "width": WIDTH,
                "height": HEIGHT,
                "boxes": [
                    {
                        "label": "positive",
                        "provenance": "hand-drawn",
                        "x": 1,
                        "y": 1,
                        "w": 2,
                        "h": 2,
                    }
                ],
            },
        )
        path = await stored_path(client, dataset["id"])

        body = await read_masks(client, dataset["id"], path)

        assert body["masks"] == []

    async def test_an_unknown_path_is_an_empty_list(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)

        body = await read_masks(client, dataset["id"], "/nowhere/x.png")

        assert body["masks"] == []

    async def test_an_unknown_dataset_is_404(self, client: AsyncClient) -> None:
        # Different question: the caller is pointed at nothing at all.
        response = await client.get(
            "/api/v1/datasets/nope/images/masks", params={"path": "/x.png"}
        )
        assert response.status_code == 404


class TestIsolation:
    async def test_masks_belong_to_one_dataset(
        self, client: AsyncClient, image_path: str
    ) -> None:
        first = await make_dataset(client, name="One")
        second = await make_dataset(client, name="Two")
        await client.put(
            f"/api/v1/datasets/{first['id']}/images/masks", json=mask_payload(image_path)
        )
        path = await stored_path(client, first["id"])

        body = await read_masks(client, second["id"], path)

        assert body["masks"] == []

    async def test_saving_replaces_rather_than_appends(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # Rule 7's other half: re-reviewing must not leave the previous set behind, which
        # is also why the Studio has to load masks before it saves.
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks",
            json=mask_payload(image_path, box=(2, 1, 3, 2)),
        )
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks",
            json=mask_payload(image_path, box=(0, 0, 2, 2)),
        )
        path = await stored_path(client, dataset["id"])

        body = await read_masks(client, dataset["id"], path)

        assert len(body["masks"]) == 1
        assert (body["masks"][0]["x"], body["masks"][0]["y"]) == (0.0, 0.0)

    async def test_an_emptied_set_clears_the_image(
        self, client: AsyncClient, image_path: str
    ) -> None:
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks", json=mask_payload(image_path)
        )
        path = await stored_path(client, dataset["id"])

        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks",
            json={"path": path, "width": WIDTH, "height": HEIGHT, "masks": []},
        )

        assert (await read_masks(client, dataset["id"], path))["masks"] == []
