"""Saved means complete (doc 117): classes added later leave older pictures unknown."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from app.finetune.phrase_data import load_phrase_table
from tests.datasets_api_testkit import dataset_client, make_dataset, mask_payload


class Clock:
    """The store's clock, one minute per `tick()`: timestamps in order, never equal."""

    def __init__(self) -> None:
        self.minute = 0

    def tick(self) -> None:
        self.minute += 1

    def now(self) -> str:
        return f"2026-09-30T10:{self.minute:02d}:00+00:00"


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    clock = Clock()
    monkeypatch.setattr("app.datasets.images.now", clock.now)
    monkeypatch.setattr("app.datasets.classes._now", clock.now)
    monkeypatch.setattr("app.datasets.store._now", clock.now)
    return clock


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: Clock
) -> AsyncGenerator[AsyncClient, None]:
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


def _masks(prompt: str, path: str) -> dict[str, Any]:
    payload = mask_payload("positive")
    payload["path"] = path
    payload["masks"][0]["prompt"] = prompt
    return payload


async def _m8_then_m10(client: AsyncClient, clock: Clock) -> str:
    """Dataset (asking for m8, m9), a.jpg saved, then class m10, then b.jpg with m10."""
    dataset = await make_dataset(client, prompt="m8, m9")
    url = f"/api/v1/datasets/{dataset['id']}"
    clock.tick()
    await client.put(f"{url}/images/masks", json=_masks("m8", "/images/a.jpg"))
    clock.tick()
    await client.post(f"{url}/classes", json={"name": "m10"})
    clock.tick()
    await client.put(f"{url}/images/masks", json=_masks("m10", "/images/b.jpg"))
    return str(dataset["id"])


async def _completeness(client: AsyncClient, dataset_id: str) -> dict[str, Any]:
    found: dict[str, Any] = (await client.get(f"/api/v1/datasets/{dataset_id}/completeness")).json()
    return found


async def _unknown(client: AsyncClient, dataset_id: str, name: str) -> list[str]:
    url = f"/api/v1/datasets/{dataset_id}/completeness/unknown"
    paths: list[str] = (await client.get(url, params={"class_name": name})).json()
    return paths


class TestCompleteness:
    async def test_a_class_made_later_leaves_the_older_pictures_unknown(
        self, client: AsyncClient, clock: Clock
    ) -> None:
        dataset_id = await _m8_then_m10(client, clock)
        found = await _completeness(client, dataset_id)
        assert found["m10"] == {"since": "2026-09-30T10:02:00+00:00", "unknown": 1}
        assert found["m8"]["unknown"] == 0
        paths = await _unknown(client, dataset_id, "m10")
        assert [p.rsplit("/", 1)[-1] for p in paths] == ["a.jpg"]

    async def test_a_prompt_term_exists_from_the_dataset_s_start(
        self, client: AsyncClient, clock: Clock
    ) -> None:
        """m9 was asked for from the start but never found: a.jpg is still known for it."""
        dataset_id = await _m8_then_m10(client, clock)
        found = await _completeness(client, dataset_id)
        assert found["m9"] == {"since": "2026-09-30T10:00:00+00:00", "unknown": 0}

    async def test_a_check_by_hand_makes_it_known(self, client: AsyncClient, clock: Clock) -> None:
        dataset_id = await _m8_then_m10(client, clock)
        paths = await _unknown(client, dataset_id, "m10")
        body = {"path": paths[0], "phrase": "m10", "status": "absent"}
        await client.put(f"/api/v1/datasets/{dataset_id}/images/phrase-status", json=body)
        assert (await _completeness(client, dataset_id))["m10"]["unknown"] == 0

    async def test_saving_again_makes_it_known(self, client: AsyncClient, clock: Clock) -> None:
        """Opening a.jpg again and saving it with m10 in the vocabulary: looked at now."""
        dataset_id = await _m8_then_m10(client, clock)
        clock.tick()
        url = f"/api/v1/datasets/{dataset_id}/images/masks"
        await client.put(url, json=_masks("m8", "/images/a.jpg"))
        assert (await _completeness(client, dataset_id))["m10"]["unknown"] == 0

    async def test_training_reads_the_same_rule(self, client: AsyncClient, clock: Clock) -> None:
        dataset_id = await _m8_then_m10(client, clock)
        table = load_phrase_table((dataset_id,))
        older = next(path for path in table.unknown if path.endswith("a.jpg"))
        assert table.unknown[older] == {"m10"}
        assert not [p for p in table.unknown if p.endswith("b.jpg")]


class TestItDoesNotOccurThere:
    """Doc 118: the first answer to 'm10 is new — does it occur in the older pictures?'"""

    async def test_marks_only_the_unknown_pictures_absent(
        self, client: AsyncClient, clock: Clock
    ) -> None:
        dataset_id = await _m8_then_m10(client, clock)
        url = f"/api/v1/datasets/{dataset_id}/completeness/absent"
        marked = await client.post(url, json={"class_name": "M10"})
        assert marked.json() == {"marked": 1}
        assert (await _completeness(client, dataset_id))["m10"]["unknown"] == 0
        again = await client.post(url, json={"class_name": "m10"})
        assert again.json() == {"marked": 0}

    async def test_training_then_learns_none_here_from_them(
        self, client: AsyncClient, clock: Clock
    ) -> None:
        dataset_id = await _m8_then_m10(client, clock)
        url = f"/api/v1/datasets/{dataset_id}/completeness/absent"
        await client.post(url, json={"class_name": "m10"})
        table = load_phrase_table((dataset_id,))
        older = next(path for path in table.statuses if path.endswith("a.jpg"))
        assert table.statuses[older] == {"m10": "absent"}

    async def test_an_unknown_class_is_refused_with_the_reason(
        self, client: AsyncClient, clock: Clock
    ) -> None:
        dataset_id = await _m8_then_m10(client, clock)
        url = f"/api/v1/datasets/{dataset_id}/completeness/absent"
        response = await client.post(
            url, json={"class_name": "m99"}, headers={"Accept-Language": "de"}
        )
        assert response.status_code == 422
        assert "Keine Klasse dieses Datensatzes: m99." in response.text
