"""What a dataset is annotated for (doc 104)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.datasets.annotation_targets import TARGETS
from app.prep.profiles import PROFILES
from tests.datasets_api_testkit import dataset_client, make_dataset


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


def _levels(target_id: str) -> dict[str, str]:
    target = next(t for t in TARGETS if t.id == target_id)
    return {rule.layer: rule.level for rule in target.layers}


class TestTheMatrix:
    def test_sam3_makes_phrases_and_checks_a_must(self) -> None:
        levels = _levels("sam3")
        assert levels["masks"] == levels["phrases"] == levels["picture-status"] == "required"
        assert levels["boxes"] == "optional"

    def test_a_classifier_needs_only_the_picture_class(self) -> None:
        levels = _levels("classifier")
        assert [k for k, v in levels.items() if v == "required"] == ["picture-class"]

    def test_open_forces_nothing_and_recommends_what_sam_needs(self) -> None:
        levels = _levels("open")
        assert "required" not in levels.values()
        assert levels["masks"] == levels["phrases"] == "recommended"

    def test_every_rule_says_why_and_every_target_covers_every_layer(self) -> None:
        for target in TARGETS:
            assert len(target.layers) == 5
            assert all(len(rule.why) > 30 for rule in target.layers), target.id

    def test_every_profile_exists_in_prepare_data(self) -> None:
        known = {p.id for p in PROFILES}
        assert all(t.profile in known for t in TARGETS if t.profile)


class TestStorage:
    async def test_open_until_set_then_remembered(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        url = f"/api/v1/datasets/{dataset['id']}/annotation-target"
        assert (await client.get(url)).json() == {"target": "open"}
        assert (await client.put(url, json={"target": "sam3"})).json() == {"target": "sam3"}
        assert (await client.get(url)).json() == {"target": "sam3"}

    async def test_unknown_target_and_dataset(self, client: AsyncClient) -> None:
        dataset = await make_dataset(client)
        bad = await client.put(
            f"/api/v1/datasets/{dataset['id']}/annotation-target", json={"target": "yolo"}
        )
        assert bad.status_code == 422
        assert (await client.get("/api/v1/datasets/nope/annotation-target")).status_code == 404

    async def test_the_matrix_is_served(self, client: AsyncClient) -> None:
        body = (await client.get("/api/v1/annotation-targets")).json()
        assert [t["id"] for t in body] == ["open", "classifier", "detector", "sam2", "sam3"]
