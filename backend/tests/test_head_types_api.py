"""Tests for GET /api/v1/head-types.

The compatibility branch is the point: with no ?backbone= the verdict is null, with an
installed one it is a real answer, and the two failure modes (unknown vs not installed)
must be distinguishable because they need different fixes.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.ml.backbone import clear_cache


@pytest.fixture(autouse=True)
def _clean_cache() -> Iterator[None]:
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path))
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def install_backbone(root: Path, model_id: str, **config: Any) -> Path:
    directory = root / model_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "patch_size": 14,
        "hidden_size": 768,
        "num_hidden_layers": 12,
        "image_size": 518,
        **config,
    }
    (directory / "config.json").write_text(json.dumps(payload))
    (directory / "model.safetensors").write_bytes(b"not real weights")
    return directory


def head_types(client: TestClient, query: str = "") -> list[dict[str, Any]]:
    response = client.get(f"/api/v1/head-types{query}")
    assert response.status_code == 200, response.text
    return response.json()["head_types"]


class TestListHeadTypes:
    def test_lists_all_four_tasks(self, client: TestClient) -> None:
        tasks = {entry["task"] for entry in head_types(client)}
        assert tasks == {"classification", "detection", "segmentation", "depth"}

    def test_compatibility_is_null_without_a_backbone(self, client: TestClient) -> None:
        assert all(entry["compatible"] is None for entry in head_types(client))

    def test_depth_is_reported_as_not_trainable(self, client: TestClient) -> None:
        depth = next(e for e in head_types(client) if e["task"] == "depth")
        assert depth["trainable"] is False
        assert depth["primary_metric"] is None

    def test_metrics_reach_the_client(self, client: TestClient) -> None:
        """The metrics stream reads these rather than hardcoding names."""
        detector = next(e for e in head_types(client) if e["task"] == "detection")
        assert "map" in detector["metrics"]
        assert detector["primary_metric"] == "map"
        assert detector["primary_metric_mode"] == "max"

    def test_dense_tasks_report_aspect_preserve(self, client: TestClient) -> None:
        for entry in head_types(client):
            if entry["task"] in {"detection", "segmentation", "depth"}:
                assert entry["geometry"] == "aspect-preserve"


class TestCompatibilityQuery:
    def test_installed_backbone_yields_verdicts(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        install_backbone(tmp_path, "dinov2-base")
        entries = head_types(client, "?backbone=dinov2-base")
        assert all(entry["compatible"] is True for entry in entries)
        assert all(entry["incompatible_reason"] is None for entry in entries)

    def test_uninstalled_backbone_is_409(self, client: TestClient) -> None:
        """Different fix from an unknown id — the user must download it, not retype it."""
        response = client.get("/api/v1/head-types?backbone=dinov2-large")
        assert response.status_code == 409
        assert "not installed" in response.json()["error"]["message"]

    def test_unknown_backbone_is_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/head-types?backbone=not-a-model")
        assert response.status_code == 404

    def test_a_detector_is_not_a_valid_backbone(self, client: TestClient) -> None:
        response = client.get("/api/v1/head-types?backbone=grounding-dino-tiny")
        assert response.status_code in {404, 409}
