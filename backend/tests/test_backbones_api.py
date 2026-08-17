"""Tests for GET /api/v1/backbones.

Covers the two things the trainer UI and head-compatibility checks depend on: only
backbones are listed, and an installed backbone reports a real descriptor while an
uninstalled one reports null.
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


def backbones(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/api/v1/backbones")
    assert response.status_code == 200
    return response.json()["backbones"]


class TestListBackbones:
    def test_lists_only_backbones(self, client: TestClient) -> None:
        """Grounding DINO is a detector — it must not appear as a trainable target."""
        ids = {entry["id"] for entry in backbones(client)}
        assert "dinov2-base" in ids
        assert not any(model_id.startswith("grounding-dino") for model_id in ids)

    def test_uninstalled_backbone_has_null_capabilities(self, client: TestClient) -> None:
        entry = next(e for e in backbones(client) if e["id"] == "dinov2-base")
        assert entry["installed"] is False
        assert entry["capabilities"] is None

    def test_installed_backbone_reports_capabilities(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        install_backbone(tmp_path, "dinov2-base")
        entry = next(e for e in backbones(client) if e["id"] == "dinov2-base")
        assert entry["installed"] is True
        assert entry["capabilities"] == {
            "patch_size": 14,
            "embed_dim": 768,
            "num_prefix_tokens": 1,
            "num_layers": 12,
            "image_size": 518,
        }

    def test_register_tokens_reach_the_api(self, client: TestClient, tmp_path: Path) -> None:
        install_backbone(tmp_path, "dinov3-vitb16", patch_size=16, num_register_tokens=4)
        entry = next(e for e in backbones(client) if e["id"] == "dinov3-vitb16")
        assert entry["capabilities"]["num_prefix_tokens"] == 5
        assert entry["capabilities"]["patch_size"] == 16

    def test_gated_flag_is_carried(self, client: TestClient) -> None:
        entry = next(e for e in backbones(client) if e["id"] == "dinov3-vitb16")
        assert entry["gated"] is True

    def test_corrupt_config_degrades_one_entry_only(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """A broken config must not blank the list — the other backbones still matter."""
        install_backbone(tmp_path, "dinov2-base")
        broken = install_backbone(tmp_path, "dinov2-small", hidden_size=384)
        (broken / "config.json").write_text("{ not json")

        entries = {entry["id"]: entry for entry in backbones(client)}
        assert entries["dinov2-small"]["capabilities"] is None
        assert entries["dinov2-small"]["installed"] is True
        assert entries["dinov2-base"]["capabilities"]["embed_dim"] == 768
