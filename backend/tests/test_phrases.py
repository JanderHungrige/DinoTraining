"""SAM 3 phrases (doc 103): variants stored once, masks linked, pictures checked."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from app.datasets.phrase_links import split_input
from tests.datasets_api_testkit import dataset_client, make_dataset, mask_payload


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


def _masks(prompt: str, *phrase_lists: list[str], path: str = "/images/a.jpg") -> dict[str, Any]:
    payload = mask_payload(*(["positive"] * len(phrase_lists)))
    payload["path"] = path
    for mask, phrases in zip(payload["masks"], phrase_lists, strict=True):
        mask["prompt"] = prompt
        mask["phrases"] = phrases
    return payload


async def _phrases(client: AsyncClient, dataset_id: str) -> dict[str, dict[str, Any]]:
    listed = (await client.get(f"/api/v1/datasets/{dataset_id}/phrases")).json()
    return {p["text"]: p for p in listed}


class TestSplitInput:
    def test_comma_separated_is_one_phrase_with_variations(self) -> None:
        assert split_input("Red car, crimson car ,car in red") == (
            "red car",
            ["crimson car", "car in red"],
        )

    def test_duplicates_and_empties_are_dropped(self) -> None:
        assert split_input("signal, , Signal., light  signal") == ("signal", ["light signal"])

    def test_nothing_is_refused(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            split_input(" , ")


class TestPhrases:
    async def test_a_class_is_its_own_phrase_without_any_migration(
        self, client: AsyncClient
    ) -> None:
        dataset = await make_dataset(client)
        await client.put(f"/api/v1/datasets/{dataset['id']}/images/masks", json=_masks("Car", []))
        phrases = await _phrases(client, dataset["id"])
        assert phrases["car"]["id"] is None
        assert phrases["car"]["instances"] == 1

    async def test_variations_are_stored_once_and_merged(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        url = f"/api/v1/datasets/{dataset['id']}/phrases"
        first = (
            await client.post(url, json={"text": "red car, crimson car", "class_name": "car"})
        ).json()
        again = (
            await client.post(url, json={"text": "red car, car in red", "class_name": "car"})
        ).json()
        assert first["id"] == again["id"]
        assert again["variants"] == ["crimson car", "car in red"]

    async def test_a_variation_cannot_be_another_phrase(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        url = f"/api/v1/datasets/{dataset['id']}/phrases"
        await client.post(url, json={"text": "crimson car", "class_name": "car"})
        refused = await client.post(url, json={"text": "red car, crimson car", "class_name": "car"})
        assert refused.status_code == 422
        assert "crimson car" in refused.json()["error"]["message"]

    async def test_a_mask_answers_to_its_class_and_its_phrases(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        base = f"/api/v1/datasets/{dataset['id']}"
        await client.put(f"{base}/images/masks", json=_masks("car", ["red car"], []))
        stored = (await client.get(f"{base}/images/masks", params={"path": "/images/a.jpg"})).json()
        assert [m["phrases"] for m in stored["masks"]] == [["car", "red car"], ["car"]]
        phrases = await _phrases(client, dataset["id"])
        # Nested concepts: both masks are cars, one is also a red car.
        assert phrases["car"]["instances"] == 2 and phrases["red car"]["instances"] == 1

    async def test_saving_again_replaces_links_but_keeps_statuses(
        self, client: AsyncClient
    ) -> None:
        dataset = await make_dataset(client)
        base = f"/api/v1/datasets/{dataset['id']}"
        await client.put(f"{base}/images/masks", json=_masks("car", ["red car"]))
        await client.put(
            f"{base}/images/phrase-status",
            json={"path": "/images/a.jpg", "phrase": "car", "status": "complete"},
        )
        await client.put(f"{base}/images/masks", json=_masks("car", []))
        phrases = await _phrases(client, dataset["id"])
        assert phrases["red car"]["instances"] == 0
        assert phrases["car"]["complete"] == 1

    async def test_a_phrase_of_another_class_is_refused(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        base = f"/api/v1/datasets/{dataset['id']}"
        await client.post(f"{base}/phrases", json={"text": "red light", "class_name": "signal"})
        refused = await client.put(f"{base}/images/masks", json=_masks("car", ["red light"]))
        assert refused.status_code == 422
        assert "class 'signal'" in refused.json()["error"]["message"]

    async def test_confusable_phrases_and_delete(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        base = f"/api/v1/datasets/{dataset['id']}/phrases"
        created = (await client.post(base, json={"text": "signal"})).json()
        changed = (
            await client.patch(
                f"{base}/{created['id']}", json={"confusable": ["Street lamp", "traffic sign"]}
            )
        ).json()
        assert changed["confusable"] == ["street lamp", "traffic sign"]
        assert (await client.delete(f"{base}/{created['id']}")).json() == {"removed": True}
        assert (await client.delete(f"{base}/{created['id']}")).status_code == 404

    async def test_coco_carries_the_phrases(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        base = f"/api/v1/datasets/{dataset['id']}"
        await client.put(f"{base}/images/masks", json=_masks("car", ["red car"]))
        written = (await client.post(f"{base}/export/coco")).json()["path"]
        coco = json.loads(Path(written).read_text())
        annotation = next(a for a in coco["annotations"] if "segmentation" in a)
        assert annotation["phrase"] == "car" and annotation["phrases"] == ["car", "red car"]


class TestPictureStatus:
    async def test_checked_absent_and_cleared(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        base = f"/api/v1/datasets/{dataset['id']}"
        await client.put(f"{base}/images/masks", json=_masks("car", []))
        url = f"{base}/images/phrase-status"
        await client.post(f"{base}/phrases", json={"text": "bus"})
        body = {"path": "/images/a.jpg", "phrase": "bus", "status": "absent"}
        statuses = (await client.put(url, json=body)).json()
        assert [(s["text"], s["status"]) for s in statuses] == [("bus", "absent")]
        await client.put(url, json=body | {"status": None})
        assert (await client.get(url, params={"path": "/images/a.jpg"})).json() == []

    async def test_an_unknown_phrase_or_picture_is_refused(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        base = f"/api/v1/datasets/{dataset['id']}"
        await client.put(f"{base}/images/masks", json=_masks("car", []))
        url = f"{base}/images/phrase-status"
        unknown = await client.put(
            url, json={"path": "/images/a.jpg", "phrase": "tram", "status": "absent"}
        )
        assert unknown.status_code == 422 and "add it first" in unknown.json()["error"]["message"]
        missing = await client.put(
            url, json={"path": "/nope.jpg", "phrase": "car", "status": "absent"}
        )
        assert missing.status_code == 404
