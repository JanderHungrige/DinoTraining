"""Umbrella terms (doc 115): "screw" over m8 and m9, stored, validated and trained on."""

from __future__ import annotations

import random
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from app.finetune.adapters.sam3_queries import QuerySettings, plan_queries
from app.finetune.phrase_data import PhraseDef, PhraseTable
from app.ml.training.samples import MaskTarget, TrainingSample
from tests.datasets_api_testkit import dataset_client, make_dataset, mask_payload


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


def _masks(*prompts: str, path: str = "/images/a.jpg") -> dict[str, Any]:
    payload = mask_payload(*(["positive"] * len(prompts)))
    payload["path"] = path
    for mask, prompt in zip(payload["masks"], prompts, strict=True):
        mask["prompt"] = prompt
    return payload


async def _screws(client: AsyncClient) -> str:
    dataset = await make_dataset(client)
    url = f"/api/v1/datasets/{dataset['id']}/images/masks"
    await client.put(url, json=_masks("m8", "m8", "m9"))
    return str(dataset["id"])


class TestStore:
    async def test_an_umbrella_counts_every_outline_of_its_classes(
        self, client: AsyncClient
    ) -> None:
        dataset_id = await _screws(client)
        url = f"/api/v1/datasets/{dataset_id}/phrases"
        created = await client.post(url, json={"text": "screw, bolt", "classes": ["m8", "M9"]})
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["umbrella"] is True
        assert body["classes"] == ["m8", "m9"]
        assert body["variants"] == ["bolt"]
        assert body["instances"] == 3
        listed = {p["text"]: p for p in (await client.get(url)).json()}
        assert listed["m8"]["classes"] == ["m8"] and listed["m8"]["umbrella"] is False

    @pytest.mark.parametrize(
        ("body", "reason"),
        [
            ({"text": "screw", "classes": ["m8"]}, "at least 2 classes"),
            ({"text": "screw", "classes": ["m8", "m10"]}, "Not a class of this dataset: m10"),
            ({"text": "m8", "classes": ["m8", "m9"]}, "already a class"),
            ({"text": "m9x", "classes": ["m8", "m9"]}, None),
        ],
    )
    async def test_refusals_say_why(
        self, client: AsyncClient, body: dict[str, Any], reason: str | None
    ) -> None:
        dataset_id = await _screws(client)
        response = await client.post(f"/api/v1/datasets/{dataset_id}/phrases", json=body)
        if reason is None:
            assert response.status_code == 201
        else:
            assert response.status_code == 422
            assert reason in response.text

    async def test_a_class_name_cannot_become_an_umbrella(self, client: AsyncClient) -> None:
        dataset_id = await _screws(client)
        await client.put(
            f"/api/v1/datasets/{dataset_id}/images/masks",
            json=_masks("m8", "m9", "nut", path="/images/b.jpg"),
        )
        response = await client.post(
            f"/api/v1/datasets/{dataset_id}/phrases", json={"text": "nut", "classes": ["m8", "m9"]}
        )
        assert response.status_code == 422
        assert "already a class" in response.text

    async def test_members_can_be_replaced_but_not_given_to_an_ordinary_phrase(
        self, client: AsyncClient
    ) -> None:
        dataset_id = await _screws(client)
        await client.put(
            f"/api/v1/datasets/{dataset_id}/images/masks", json=_masks("m10", path="/images/b.jpg")
        )
        url = f"/api/v1/datasets/{dataset_id}/phrases"
        screw = (await client.post(url, json={"text": "screw", "classes": ["m8", "m9"]})).json()
        changed = await client.patch(f"{url}/{screw['id']}", json={"classes": ["m8", "m9", "m10"]})
        assert changed.json()["classes"] == ["m10", "m8", "m9"]
        plain = (await client.post(url, json={"text": "red m8", "class_name": "m8"})).json()
        refused = await client.patch(f"{url}/{plain['id']}", json={"classes": ["m8", "m9"]})
        assert refused.status_code == 422
        assert "only an umbrella term" in refused.text

    async def test_an_umbrella_is_never_linked_to_one_outline(self, client: AsyncClient) -> None:
        dataset_id = await _screws(client)
        await client.post(
            f"/api/v1/datasets/{dataset_id}/phrases",
            json={"text": "screw", "classes": ["m8", "m9"]},
        )
        payload = _masks("m8")
        payload["masks"][0]["phrases"] = ["screw"]
        response = await client.put(f"/api/v1/datasets/{dataset_id}/images/masks", json=payload)
        assert response.status_code == 422
        assert "umbrella term" in response.text


# --- Training (sam3_queries) -----------------------------------------------------------

NAMES = ("m8", "m9", "nut")
NONE = QuerySettings(num_negatives=0)


def sample(*classes: int, unclear: tuple[int, ...] = ()) -> TrainingSample:
    masks = tuple(MaskTarget(c, (4, 4), (i, 1, 15 - i)) for i, c in enumerate(classes))
    ignore = tuple(MaskTarget(c, (4, 4), (0, 16)) for c in unclear)
    return TrainingSample(
        path="/a", width=4, height=4, masks=masks, segmented=True, ignore_masks=ignore
    )


def table(**statuses: dict[str, str]) -> PhraseTable:
    return PhraseTable(
        phrases={"screw": PhraseDef("screw", "", classes=("m8", "m9"))},
        statuses=dict(statuses),
    )


def queries(s: TrainingSample, t: PhraseTable) -> list[tuple[str, str, tuple[int, ...]]]:
    return [(q.text, q.kind, q.masks) for q in plan_queries(s, NAMES, t, NONE, random.Random(0))]


class TestTraining:
    def test_screw_is_answered_by_every_m8_and_m9_outline(self) -> None:
        planned = queries(sample(0, 1, 2), table())
        assert ("screw", "positive", (0, 1)) in planned
        assert ("m8", "positive", (0,)) in planned

    def test_no_screw_on_a_picture_with_neither_is_a_negative(self) -> None:
        assert ("screw", "cross", ()) in queries(sample(2), table())

    def test_screw_is_never_a_negative_where_a_member_is_present(self) -> None:
        planned = queries(sample(0), table())
        assert ("screw", "positive", (0,)) in planned
        assert not [q for q in planned if q[0] == "screw" and q[1] != "positive"]

    def test_an_unknown_member_leaves_the_umbrella_out(self) -> None:
        """m9 checked elsewhere but not here: its screws here may be unoutlined."""
        checked_elsewhere = table(**{"/other": {"m9": "complete"}})
        assert not [q for q in queries(sample(0), checked_elsewhere) if q[0] == "screw"]

    def test_an_unclear_member_leaves_the_umbrella_out(self) -> None:
        assert not [q for q in queries(sample(0, unclear=(1,)), table()) if q[0] == "screw"]

    def test_checked_members_make_a_checked_negative(self) -> None:
        checked = table(**{"/a": {"m8": "absent", "m9": "absent"}})
        assert ("screw", "absent", ()) in queries(sample(2), checked)
