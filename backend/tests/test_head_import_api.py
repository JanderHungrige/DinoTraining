"""Tests for POST /api/v1/heads/import — the untrusted-source endpoint.

Split from test_head_catalog_api.py: the catalogue endpoints serve a fixed table,
while this one is the app's front door for a user-named repository. They fail in
different ways and are worth reading separately.
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
from app.ml.heads.register import IncompatibleHeadError
from tests.head_testkit import install_fake_backbone


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


def patch_repo(monkeypatch: pytest.MonkeyPatch, files: list[str], local: Path | None) -> None:
    monkeypatch.setattr("app.ml.heads.importer._list_repo_files", lambda repo_id: files)
    if local is not None:
        monkeypatch.setattr(
            "app.ml.heads.importer._download_repo_file",
            lambda repo_id, filename, token: local,
        )


class TestImport:
    def payload(self, **overrides: object) -> dict[str, object]:
        body: dict[str, object] = {
            "repo_id": "someone/probe",
            "head_type_id": "linear-classifier",
            "backbone_id": "dinov2-small",
            "num_classes": 2,
        }
        body.update(overrides)
        return body

    def test_invalid_repo_id_is_400(self, client: TestClient) -> None:
        with_backbone()
        response = client.post(
            "/api/v1/heads/import", json=self.payload(repo_id="../../etc/passwd")
        )
        assert response.status_code == 400

    def test_pickle_only_repo_is_415(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """415 rather than 400: the request was fine, the repo's format is not.

        The real refusal is exercised rather than stubbed, so this also asserts the
        message the user sees survives the trip through the exception handler.
        """
        with_backbone()
        monkeypatch.setattr(
            "app.ml.heads.importer._list_repo_files",
            lambda repo_id: ["config.json", "pytorch_model.pth"],
        )
        response = client.post("/api/v1/heads/import", json=self.payload())
        assert response.status_code == 415
        assert "safetensors" in response.json()["error"]["message"].lower()

    def test_uninstalled_backbone_is_409(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/heads/import", json=self.payload(backbone_id="dinov2-large")
        )
        assert response.status_code == 409

    def test_incompatible_weights_are_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with_backbone()

        def boom(**kwargs: object) -> None:
            raise IncompatibleHeadError("These weights do not fit (embed_dim 384)")

        monkeypatch.setattr("app.api.v1.head_catalog.import_community_head", boom)
        response = client.post("/api/v1/heads/import", json=self.payload())
        assert response.status_code == 422
        assert "embed_dim" in response.json()["error"]["message"]

    def test_successful_import_is_201(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from safetensors.torch import save_file

        with_backbone()
        head_file = tmp_path / "model.safetensors"
        save_file(
            {"linear.weight": torch.randn(2, 384), "linear.bias": torch.randn(2)},
            str(head_file),
        )
        monkeypatch.setattr(
            "app.ml.heads.importer._list_repo_files", lambda repo_id: ["model.safetensors"]
        )
        monkeypatch.setattr(
            "app.ml.heads.importer._download_repo_file",
            lambda repo_id, filename, token: head_file,
        )

        response = client.post("/api/v1/heads/import", json=self.payload())
        assert response.status_code == 201
        body = response.json()
        assert body["kind"] == "community"
        assert body["source_repo"] == "someone/probe"

    def test_omitting_num_classes_does_not_500(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Regression: the real form leaves Classes blank and got a 500 from build_head."""
        from safetensors.torch import save_file

        with_backbone()
        head_file = tmp_path / "model.safetensors"
        save_file(
            {"linear.weight": torch.randn(5, 384), "linear.bias": torch.randn(5)},
            str(head_file),
        )
        monkeypatch.setattr(
            "app.ml.heads.importer._list_repo_files", lambda repo_id: ["model.safetensors"]
        )
        monkeypatch.setattr(
            "app.ml.heads.importer._download_repo_file",
            lambda repo_id, filename, token: head_file,
        )

        body = self.payload()
        del body["num_classes"]
        response = client.post("/api/v1/heads/import", json=body)

        assert response.status_code == 201, response.text
        assert response.json()["num_classes"] == 5

    def test_missing_fields_are_422(self, client: TestClient) -> None:
        assert client.post("/api/v1/heads/import", json={"repo_id": "a/b"}).status_code == 422
