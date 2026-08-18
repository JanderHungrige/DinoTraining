"""Tests for GET /head-catalog and POST /head-catalog/{id}/install.

Status codes carry meaning here and the UI branches on them: 409 means "do something
first", 422 means "these bytes are wrong", 503 means "try later". A blanket 400 would
collapse three different fixes into one unhelpful message.

The import endpoint is covered in test_head_import_api.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import torch
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.main import create_app
from app.ml.heads.convert import DigestMismatchError, UpstreamUnavailableError
from tests.head_testkit import install_fake_backbone, upstream_depth

DEPTH_ENTRY = "dinov2-linear-depth-nyu.dinov2-small"
CATALOG = "/api/v1/head-catalog"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_connection()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_connection()
    get_settings.cache_clear()


def with_backbone(model_id: str = "dinov2-small", embed_dim: int = 384) -> None:
    install_fake_backbone(get_settings(), model_id, embed_dim)


def patch_install(monkeypatch: pytest.MonkeyPatch, payload: dict[str, torch.Tensor]) -> None:
    def fake_download(entry: object, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        torch.save(payload, destination)
        return destination

    monkeypatch.setattr("app.ml.heads.install.download_entry", fake_download)
    monkeypatch.setattr(
        "app.ml.heads.convert.verify_digest", lambda path, expected: expected
    )


class TestListCatalog:
    def test_lists_every_entry(self, client: TestClient) -> None:
        body = client.get(CATALOG).json()
        assert len(body["entries"]) == 9

    def test_entry_shape(self, client: TestClient) -> None:
        entry = next(
            item for item in client.get(CATALOG).json()["entries"] if item["id"] == DEPTH_ENTRY
        )
        assert entry["task"] == "depth"
        assert entry["backbone_id"] == "dinov2-small"
        assert entry["licence"] == "Apache-2.0"
        assert entry["trained_on"] == "NYU Depth v2"
        assert entry["size_bytes"] > 0
        assert entry["installed"] is False
        assert entry["installed_instance_id"] is None

    def test_compatibility_is_null_without_a_backbone_query(self, client: TestClient) -> None:
        """Matches GET /head-types: no verdict is offered unless one was asked for."""
        for entry in client.get(CATALOG).json()["entries"]:
            assert entry["compatible"] is None
            assert entry["incompatible_reason"] is None

    def test_matching_backbone_entries_are_compatible(self, client: TestClient) -> None:
        with_backbone()
        entries = client.get(CATALOG, params={"backbone": "dinov2-small"}).json()["entries"]
        mine = [entry for entry in entries if entry["backbone_id"] == "dinov2-small"]
        assert len(mine) == 3
        assert all(entry["compatible"] is True for entry in mine)
        assert all(entry["incompatible_reason"] is None for entry in mine)

    def test_other_backbone_entries_say_which_backbone_they_need(
        self, client: TestClient
    ) -> None:
        """Not merely 'incompatible' — the user's next move depends on knowing which."""
        with_backbone()
        entries = client.get(CATALOG, params={"backbone": "dinov2-small"}).json()["entries"]
        others = [entry for entry in entries if entry["backbone_id"] != "dinov2-small"]
        assert len(others) == 6
        for entry in others:
            assert entry["compatible"] is False
            assert entry["backbone_id"] in entry["incompatible_reason"]

    def test_dinov3_backbone_is_refused_with_a_reason(self, client: TestClient) -> None:
        """The wave rule: explain, never grey out."""
        with_backbone("dinov3-vitb16", 768)
        entries = client.get(CATALOG, params={"backbone": "dinov3-vitb16"}).json()["entries"]
        assert entries
        for entry in entries:
            assert entry["compatible"] is False
            assert "dinov3" in entry["incompatible_reason"]

    def test_uninstalled_backbone_is_reported_not_fatal(self, client: TestClient) -> None:
        """The user must still see the catalogue before downloading a backbone."""
        response = client.get(CATALOG, params={"backbone": "dinov2-large"})
        assert response.status_code == 200
        entries = [
            item for item in response.json()["entries"] if item["backbone_id"] == "dinov2-large"
        ]
        assert all(entry["backbone_installed"] is False for entry in entries)

    def test_unknown_backbone_is_404(self, client: TestClient) -> None:
        response = client.get(CATALOG, params={"backbone": "not-a-backbone"})
        assert response.status_code == 404

    def test_installed_entry_is_marked(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with_backbone()
        patch_install(monkeypatch, upstream_depth(384))
        created = client.post(f"{CATALOG}/{DEPTH_ENTRY}/install").json()

        entry = next(
            item for item in client.get(CATALOG).json()["entries"] if item["id"] == DEPTH_ENTRY
        )
        assert entry["installed"] is True
        assert entry["installed_instance_id"] == created["id"]


class TestInstall:
    def test_installs_and_returns_the_instance(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with_backbone()
        patch_install(monkeypatch, upstream_depth(384))

        response = client.post(f"{CATALOG}/{DEPTH_ENTRY}/install")
        assert response.status_code == 201
        body = response.json()
        assert body["kind"] == "pretrained-default"
        assert body["task"] == "depth"
        assert "Depth estimation" in body["summary"]

    def test_the_new_head_is_visible_in_the_picker(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with_backbone()
        patch_install(monkeypatch, upstream_depth(384))
        client.post(f"{CATALOG}/{DEPTH_ENTRY}/install")

        heads = client.get("/api/v1/heads", params={"task": "depth"}).json()["heads"]
        assert len(heads) == 1
        assert heads[0]["kind"] == "pretrained-default"

    def test_unknown_entry_is_404(self, client: TestClient) -> None:
        assert client.post(f"{CATALOG}/nope.nope/install").status_code == 404

    def test_uninstalled_backbone_is_409(self, client: TestClient) -> None:
        response = client.post(f"{CATALOG}/{DEPTH_ENTRY}/install")
        assert response.status_code == 409
        assert "download" in response.json()["error"]["message"].lower()

    def test_second_install_is_409(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with_backbone()
        patch_install(monkeypatch, upstream_depth(384))
        client.post(f"{CATALOG}/{DEPTH_ENTRY}/install")

        assert client.post(f"{CATALOG}/{DEPTH_ENTRY}/install").status_code == 409

    def test_digest_mismatch_is_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A tampered or changed upstream file must not read as a network problem."""
        with_backbone()

        def boom(entry: object, destination: Path) -> Path:
            raise DigestMismatchError("Digest mismatch for x: expected a, got b. Not read.")

        monkeypatch.setattr("app.ml.heads.install.download_entry", boom)
        assert client.post(f"{CATALOG}/{DEPTH_ENTRY}/install").status_code == 422

    def test_upstream_unreachable_is_503(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with_backbone()

        def boom(entry: object, destination: Path) -> Path:
            raise UpstreamUnavailableError("Could not download: URLError")

        monkeypatch.setattr("app.ml.heads.install.download_entry", boom)
        assert client.post(f"{CATALOG}/{DEPTH_ENTRY}/install").status_code == 503
