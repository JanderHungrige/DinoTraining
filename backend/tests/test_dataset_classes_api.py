"""The class vocabulary endpoints (doc 60), through the real ASGI app.

The load-bearing property is the **union**: a dataset annotated before `dataset_classes`
existed has classes on its boxes and no rows in the table, and the picker has to open full
rather than empty. Reading only the table is the failure this file exists to catch.
"""

from __future__ import annotations

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


def annotation(*classes: str, path: str = "/images/a.jpg") -> dict[str, Any]:
    """One image whose boxes carry the given classes as `prompt`."""
    return {
        "path": path,
        "width": 200,
        "height": 200,
        "boxes": [
            {
                "label": "positive",
                "provenance": "grounding-dino",
                "prompt": name,
                "x": 10,
                "y": 10,
                "w": 20,
                "h": 20,
            }
            for name in classes
        ],
    }


async def names(client: AsyncClient, dataset_id: str) -> list[str]:
    response = await client.get(f"/api/v1/datasets/{dataset_id}/classes")
    assert response.status_code == 200
    return [entry["name"] for entry in response.json()["classes"]]


class TestListing:
    async def test_a_new_dataset_has_no_classes(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        assert await names(client, dataset["id"]) == []

    async def test_it_infers_classes_from_boxes_alone(self, client: AsyncClient) -> None:
        # The pre-doc-60 dataset. Nothing was ever created; the classes arrived on boxes,
        # and the picker must still open with all of them.
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images",
            json=annotation("signal", "mast"),
        )

        assert await names(client, dataset["id"]) == ["mast", "signal"]

    async def test_an_inferred_class_reports_its_box_count(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images",
            json=annotation("signal", "signal", "mast"),
        )

        body = (await client.get(f"/api/v1/datasets/{dataset['id']}/classes")).json()
        by_name = {entry["name"]: entry for entry in body["classes"]}
        assert by_name["signal"] == {"name": "signal", "boxes": 2, "stored": False}
        assert by_name["mast"]["boxes"] == 1

    async def test_it_unions_stored_and_in_use(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images", json=annotation("signal")
        )
        await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "pedestrian"}
        )

        assert await names(client, dataset["id"]) == ["pedestrian", "signal"]

    async def test_a_created_class_reports_no_boxes(self, client: AsyncClient) -> None:
        # "Created, not yet used" is a real state and must be distinguishable.
        dataset = await make_dataset(client)
        await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "pedestrian"}
        )

        body = (await client.get(f"/api/v1/datasets/{dataset['id']}/classes")).json()
        assert body["classes"] == [{"name": "pedestrian", "boxes": 0, "stored": True}]

    async def test_it_sorts_case_insensitively(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images", json=annotation("Zebra", "apple")
        )

        # A case-sensitive sort would put every capitalised name before every lower-case
        # one, which is not an order any reviewer is looking for.
        assert await names(client, dataset["id"]) == ["apple", "Zebra"]

    async def test_it_ignores_boxes_with_no_class(self, client: AsyncClient) -> None:
        # Wave 1 wrote empty strings for an unnamed box; `prompt` is also nullable.
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images",
            json={
                "path": "/images/a.jpg",
                "width": 200,
                "height": 200,
                "boxes": [
                    {
                        "label": "positive",
                        "provenance": "hand-drawn",
                        "prompt": "  ",
                        "x": 1,
                        "y": 1,
                        "w": 2,
                        "h": 2,
                    }
                ],
            },
        )

        assert await names(client, dataset["id"]) == []

    async def test_unknown_dataset_is_404(self, client: AsyncClient) -> None:
        # Not an empty list: a typo'd id would otherwise read as a fresh dataset.
        response = await client.get("/api/v1/datasets/nope/classes")
        assert response.status_code == 404


class TestCreating:
    async def test_it_creates_and_returns_the_whole_vocabulary(
        self, client: AsyncClient
    ) -> None:
        dataset = await make_dataset(client)

        response = await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "pedestrian"}
        )

        assert response.status_code == 201
        assert [e["name"] for e in response.json()["classes"]] == ["pedestrian"]

    async def test_creating_the_same_class_twice_is_200_not_409(
        self, client: AsyncClient
    ) -> None:
        # Two reviewers creating `pedestrian` is not a conflict to resolve.
        dataset = await make_dataset(client)
        await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "pedestrian"}
        )

        again = await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "pedestrian"}
        )

        assert again.status_code == 200
        assert await names(client, dataset["id"]) == ["pedestrian"]

    async def test_case_only_differences_are_the_same_class(
        self, client: AsyncClient
    ) -> None:
        dataset = await make_dataset(client)
        await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "Pedestrian"}
        )

        again = await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "pedestrian"}
        )

        assert again.status_code == 200
        # First spelling wins — two entries differing only in case is a data-entry
        # accident, never an intent.
        assert await names(client, dataset["id"]) == ["Pedestrian"]

    async def test_it_trims_the_name(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)

        await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "  pedestrian  "}
        )

        assert await names(client, dataset["id"]) == ["pedestrian"]

    async def test_whitespace_only_is_422_not_500(self, client: AsyncClient) -> None:
        # The ValueError backstop CLAUDE.md requires: a validation failure must never
        # surface as a 500 with the reason only in the log.
        dataset = await make_dataset(client)

        response = await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "   "}
        )

        assert response.status_code == 422

    async def test_an_oversized_name_is_422(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)

        response = await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "x" * 101}
        )

        assert response.status_code == 422

    async def test_creating_promotes_an_inferred_class_to_stored(
        self, client: AsyncClient
    ) -> None:
        # What makes a class survive the last box carrying it being deleted.
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images", json=annotation("signal")
        )

        response = await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "signal"}
        )

        assert response.status_code == 201
        entry = next(e for e in response.json()["classes"] if e["name"] == "signal")
        assert entry == {"name": "signal", "boxes": 1, "stored": True}

    async def test_unknown_dataset_is_404(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/datasets/nope/classes", json={"name": "a"})
        assert response.status_code == 404


class TestDeleting:
    async def test_it_removes_an_unused_class(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "pedestrian"}
        )

        response = await client.delete(
            f"/api/v1/datasets/{dataset['id']}/classes/pedestrian"
        )

        assert response.status_code == 200
        assert response.json()["classes"] == []

    async def test_it_never_touches_a_box(self, client: AsyncClient) -> None:
        # The whole reason delete is safe to offer. Forty annotations must not be
        # rewritten or orphaned by a picker's delete affordance.
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images", json=annotation("signal")
        )
        await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "signal"}
        )

        response = await client.delete(f"/api/v1/datasets/{dataset['id']}/classes/signal")

        assert response.status_code == 200
        # Still there, and honest about why: the boxes still carry it.
        assert response.json()["classes"] == [
            {"name": "signal", "boxes": 1, "stored": False}
        ]
        images = (await client.get(f"/api/v1/datasets/{dataset['id']}/images")).json()
        assert images["images"][0]["boxes"][0]["prompt"] == "signal"

    async def test_deleting_an_inferred_class_is_404(self, client: AsyncClient) -> None:
        # There was no row to remove; reporting success would claim an effect that did
        # not happen.
        dataset = await make_dataset(client)
        await client.put(
            f"/api/v1/datasets/{dataset['id']}/images", json=annotation("signal")
        )

        response = await client.delete(f"/api/v1/datasets/{dataset['id']}/classes/signal")

        assert response.status_code == 404

    async def test_unknown_dataset_is_404(self, client: AsyncClient) -> None:
        response = await client.delete("/api/v1/datasets/nope/classes/a")
        assert response.status_code == 404


class TestIsolation:
    async def test_a_class_belongs_to_one_dataset(self, client: AsyncClient) -> None:
        first = await make_dataset(client, name="One")
        second = await make_dataset(client, name="Two")
        await client.post(
            f"/api/v1/datasets/{first['id']}/classes", json={"name": "pedestrian"}
        )

        assert await names(client, second["id"]) == []

    async def test_deleting_a_dataset_takes_its_classes(self, client: AsyncClient) -> None:
        # ON DELETE CASCADE, which only works because db.py turns foreign keys on.
        dataset = await make_dataset(client)
        await client.post(
            f"/api/v1/datasets/{dataset['id']}/classes", json={"name": "pedestrian"}
        )
        await client.delete(f"/api/v1/datasets/{dataset['id']}")

        recreated = await make_dataset(client, name="Cats again")
        assert await names(client, recreated["id"]) == []
