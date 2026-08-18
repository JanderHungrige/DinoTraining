"""Tests for GET/DELETE /api/v1/heads — the picker contract Waves 3 and 4 consume."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import torch
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.main import create_app
from app.ml.heads.store import HeadInstanceStore


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    reset_connection()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_connection()
    get_settings.cache_clear()


def add(**overrides: object) -> str:
    base: dict[str, object] = {
        "name": "Detector",
        "kind": "trained-here",
        "head_type_id": "dense-detector",
        "task": "detection",
        "backbone_id": "dinov2-small",
        "backbone_family": "dinov2",
        "embed_dim": 384,
        "num_classes": 2,
        "weights": {"w": torch.zeros(2, 4)},
        "class_names": ("a cat", "a dog"),
        "dataset_ids": ("ds1",),
        "metrics": {"map": 0.52},
        "primary_metric": "map",
        "primary_metric_value": 0.52,
    }
    base.update(overrides)
    return HeadInstanceStore().register(**base).id  # type: ignore[arg-type]


def heads(client: TestClient, query: str = "") -> list[dict[str, Any]]:
    response = client.get(f"/api/v1/heads{query}")
    assert response.status_code == 200, response.text
    return response.json()["heads"]


class TestListHeads:
    def test_empty_by_default(self, client: TestClient) -> None:
        assert heads(client) == []

    def test_lists_a_registered_head(self, client: TestClient) -> None:
        add()
        assert len(heads(client)) == 1

    def test_every_entry_carries_a_summary(self, client: TestClient) -> None:
        """Waves 3 and 4 render this; without it they would show hex ids."""
        add()
        entry = heads(client)[0]
        assert entry["summary"]
        assert "Object detection" in entry["summary"]

    def test_filters_by_task(self, client: TestClient) -> None:
        add()
        add(task="classification", head_type_id="linear-classifier")
        assert [e["task"] for e in heads(client, "?task=detection")] == ["detection"]

    def test_filters_by_backbone(self, client: TestClient) -> None:
        add()
        add(backbone_id="dinov2-base")
        assert len(heads(client, "?backbone=dinov2-base")) == 1

    def test_class_names_reach_the_client_in_order(self, client: TestClient) -> None:
        add(class_names=("zebra", "ant"), num_classes=2)
        assert heads(client)[0]["class_names"] == ["zebra", "ant"]

    def test_metrics_are_exposed(self, client: TestClient) -> None:
        add()
        entry = heads(client)[0]
        assert entry["metrics"]["map"] == pytest.approx(0.52)
        assert entry["primary_metric"] == "map"


class TestGetHead:
    def test_returns_the_full_record(self, client: TestClient) -> None:
        instance_id = add()
        response = client.get(f"/api/v1/heads/{instance_id}")
        assert response.status_code == 200
        assert response.json()["id"] == instance_id

    def test_unknown_head_is_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/heads/not-a-head")
        assert response.status_code == 404
        assert "Unknown head" in response.json()["error"]["message"]


class TestDeleteHead:
    def test_removes_the_head(self, client: TestClient) -> None:
        instance_id = add()
        response = client.delete(f"/api/v1/heads/{instance_id}")
        assert response.status_code == 200
        assert response.json()["removed"] is True
        assert heads(client) == []

    def test_deleting_twice_is_not_an_error(self, client: TestClient) -> None:
        """The caller wanted it gone; it is gone. Not a failure worth surfacing."""
        instance_id = add()
        client.delete(f"/api/v1/heads/{instance_id}")
        response = client.delete(f"/api/v1/heads/{instance_id}")
        assert response.status_code == 200
        assert response.json()["removed"] is False
