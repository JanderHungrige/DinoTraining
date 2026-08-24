"""Tests for the annotator endpoints, through the real ASGI app.

Readiness is the interesting part: it is a property of a *set* of models, so a
half-installed Grounded SAM must report not-ready and say which model is missing.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


def install(tmp_path: Path, model_id: str) -> None:
    """Make a model look installed — a directory with a weights file in it."""
    directory = tmp_path / "models" / model_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "model.safetensors").write_bytes(b"not really weights")
    (directory / "config.json").write_text("{}")


class TestList:
    def test_it_lists_both_annotators(self, client: TestClient) -> None:
        body = client.get("/api/v1/annotators").json()
        assert [a["id"] for a in body["annotators"]] == ["grounded-sam", "sam3"]

    def test_nothing_is_ready_on_a_clean_install(self, client: TestClient) -> None:
        body = client.get("/api/v1/annotators").json()
        assert all(a["ready"] is False for a in body["annotators"])

    def test_it_reports_licence_and_size_before_any_download(
        self, client: TestClient
    ) -> None:
        """Licence and size must be visible up front, not after the bytes land."""
        body = client.get("/api/v1/annotators").json()
        by_id = {a["id"]: a for a in body["annotators"]}
        assert by_id["grounded-sam"]["licence"] == "Apache-2.0"
        assert "SAM License" in by_id["sam3"]["licence"]
        assert by_id["sam3"]["approx_size_mb"] > 3000
        assert by_id["grounded-sam"]["approx_size_mb"] > 0

    def test_sam3_is_the_only_one_requiring_an_access_request(
        self, client: TestClient
    ) -> None:
        body = client.get("/api/v1/annotators").json()
        requiring = [a["id"] for a in body["annotators"] if a["requires_access_request"]]
        assert requiring == ["sam3"]


class TestReadiness:
    def test_a_half_installed_annotator_is_not_ready(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Grounded SAM needs two models; one is not enough and must say which is missing."""
        install(tmp_path, "grounding-dino-tiny")

        body = client.get("/api/v1/annotators/grounded-sam").json()
        assert body["ready"] is False
        assert body["missing_model_ids"] == ["sam2.1-hiera-small"]

    def test_it_becomes_ready_when_every_model_is_installed(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        install(tmp_path, "grounding-dino-tiny")
        install(tmp_path, "sam2.1-hiera-small")

        body = client.get("/api/v1/annotators/grounded-sam").json()
        assert body["ready"] is True
        assert body["missing_model_ids"] == []
        assert all(model["installed"] for model in body["models"])

    def test_grounded_sam_is_ready_without_any_gated_download(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """The claim the whole ungated path rests on."""
        install(tmp_path, "grounding-dino-tiny")
        install(tmp_path, "sam2.1-hiera-small")

        body = client.get("/api/v1/annotators/grounded-sam").json()
        assert body["ready"] is True
        assert body["gated"] is False
        assert all(model["gated"] is False for model in body["models"])

    def test_installing_one_annotator_does_not_ready_the_other(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        install(tmp_path, "grounding-dino-tiny")
        install(tmp_path, "sam2.1-hiera-small")

        body = client.get("/api/v1/annotators/sam3").json()
        assert body["ready"] is False
        assert body["missing_model_ids"] == ["sam3"]


class TestDetail:
    def test_an_unknown_annotator_is_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/annotators/not-real")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_each_required_model_carries_its_own_licence_url(
        self, client: TestClient
    ) -> None:
        body = client.get("/api/v1/annotators/grounded-sam").json()
        for model in body["models"]:
            assert model["licence_url"].startswith("https://huggingface.co/")
            assert model["id"].split(".")[0] in model["licence_url"] or model["name"]
