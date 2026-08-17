"""Tests for the model catalogue, download and removal endpoints.

No network: ``snapshot_download`` is patched. What is exercised is the routing,
the gating rules, the conflict handling and the confinement of every filesystem op.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.fixture
def cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the whole app at a throwaway cache directory."""
    root = tmp_path / "models"
    root.mkdir()
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(root))
    get_settings.cache_clear()
    return root


@pytest.fixture
async def client(cache_dir: Path) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def install(cache_dir: Path, model_id: str, size: int = 2048) -> Path:
    """Fake an installed model on disk."""
    directory = cache_dir / model_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "config.json").write_bytes(b"x" * size)
    return directory


class TestListModels:
    async def test_returns_the_whole_catalogue(self, client: AsyncClient) -> None:
        body = (await client.get("/api/v1/models")).json()
        assert len(body["models"]) == 7

    async def test_reports_not_installed_for_an_empty_cache(self, client: AsyncClient) -> None:
        body = (await client.get("/api/v1/models")).json()
        assert all(model["installed"] is False for model in body["models"])

    async def test_reports_installed_models(self, client: AsyncClient, cache_dir: Path) -> None:
        install(cache_dir, "dinov2-base")
        body = (await client.get("/api/v1/models")).json()
        entry = next(m for m in body["models"] if m["id"] == "dinov2-base")
        assert entry["installed"] is True

    async def test_gated_models_are_unavailable_without_a_token(
        self, client: AsyncClient
    ) -> None:
        body = (await client.get("/api/v1/models")).json()
        gated = [m for m in body["models"] if m["gated"]]
        assert gated
        for model in gated:
            assert model["available"] is False
            assert "licence" in (model["unavailable_reason"] or "").lower()

    async def test_open_models_are_available_without_a_token(self, client: AsyncClient) -> None:
        body = (await client.get("/api/v1/models")).json()
        for model in body["models"]:
            if not model["gated"]:
                assert model["available"] is True
                assert model["unavailable_reason"] is None

    async def test_gated_models_become_available_with_a_token(
        self, cache_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HF_TOKEN", "hf_testtoken")
        get_settings.cache_clear()
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            body = (await ac.get("/api/v1/models")).json()
        assert all(model["available"] for model in body["models"])

    async def test_response_never_contains_the_token(
        self, cache_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HF_TOKEN", "hf_supersecretvalue")
        get_settings.cache_clear()
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            raw = (await ac.get("/api/v1/models")).text
        assert "hf_supersecretvalue" not in raw


class TestDownload:
    async def test_unknown_model_is_404(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/models/not-a-model/download")
        assert response.status_code == 404

    async def test_traversal_id_is_404_not_a_filesystem_error(
        self, client: AsyncClient
    ) -> None:
        """The registry lookup runs first, so `../` never reaches a path join."""
        response = await client.post("/api/v1/models/..%2F..%2Fetc/download")
        assert response.status_code == 404

    async def test_gated_model_without_token_is_403(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/models/dinov3-vitb16/download")
        assert response.status_code == 403
        assert "licence" in response.json()["error"]["message"].lower()

    async def test_already_installed_is_409(
        self, client: AsyncClient, cache_dir: Path
    ) -> None:
        install(cache_dir, "dinov2-small")
        response = await client.post("/api/v1/models/dinov2-small/download")
        assert response.status_code == 409

    async def test_starts_a_job_and_reports_progress(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        started = asyncio.Event()

        def fake_download(**kwargs: Any) -> None:
            started.set()

        monkeypatch.setattr("huggingface_hub.snapshot_download", fake_download)

        response = await client.post("/api/v1/models/dinov2-small/download")
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        assert response.json()["state"] in ("pending", "downloading")

        await asyncio.wait_for(started.wait(), timeout=5)
        for _ in range(50):
            body = (await client.get(f"/api/v1/models/jobs/{job_id}")).json()
            if body["state"] in ("complete", "failed"):
                break
            await asyncio.sleep(0.05)
        assert body["state"] == "complete"

    async def test_a_failing_download_is_reported_without_leaking_the_message(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(**kwargs: Any) -> None:
            raise RuntimeError("token=hf_supersecretvalue in url")

        monkeypatch.setattr("huggingface_hub.snapshot_download", boom)

        job_id = (await client.post("/api/v1/models/dinov2-small/download")).json()["job_id"]
        for _ in range(50):
            body = (await client.get(f"/api/v1/models/jobs/{job_id}")).json()
            if body["state"] in ("complete", "failed"):
                break
            await asyncio.sleep(0.05)

        assert body["state"] == "failed"
        assert "hf_supersecretvalue" not in body["message"]
        assert "RuntimeError" in body["message"]

    async def test_unknown_job_is_404(self, client: AsyncClient) -> None:
        assert (await client.get("/api/v1/models/jobs/nope")).status_code == 404


class TestDelete:
    async def test_unknown_model_is_404(self, client: AsyncClient) -> None:
        assert (await client.delete("/api/v1/models/not-a-model")).status_code == 404

    async def test_removes_an_installed_model(
        self, client: AsyncClient, cache_dir: Path
    ) -> None:
        directory = install(cache_dir, "dinov2-base", size=3 * 1024 * 1024)
        response = await client.delete("/api/v1/models/dinov2-base")

        assert response.status_code == 200
        assert response.json()["removed"] is True
        assert response.json()["freed_mb"] == 3
        assert not directory.exists()

    async def test_deleting_a_missing_model_is_a_no_op(self, client: AsyncClient) -> None:
        body = (await client.delete("/api/v1/models/dinov2-large")).json()
        assert body["removed"] is False
        assert body["freed_mb"] == 0

    async def test_delete_leaves_the_cache_root_intact(
        self, client: AsyncClient, cache_dir: Path
    ) -> None:
        install(cache_dir, "dinov2-base")
        install(cache_dir, "dinov2-small")

        await client.delete("/api/v1/models/dinov2-base")

        assert cache_dir.is_dir()
        assert (cache_dir / "dinov2-small").is_dir()


class TestSystemInfo:
    async def test_reports_device_and_cache_dir(
        self, client: AsyncClient, cache_dir: Path
    ) -> None:
        body = (await client.get("/api/v1/system/info")).json()
        assert body["device"] in {"cuda", "mps", "cpu"}
        assert body["cache_dir"] == str(cache_dir.resolve())
        assert body["free_disk_mb"] > 0

    async def test_reports_token_absence_as_a_boolean(self, client: AsyncClient) -> None:
        body = (await client.get("/api/v1/system/info")).json()
        assert body["hf_token_present"] is False

    async def test_never_returns_the_token_itself(
        self, cache_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HF_TOKEN", "hf_supersecretvalue")
        get_settings.cache_clear()
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/system/info")

        assert response.json()["hf_token_present"] is True
        assert "hf_supersecretvalue" not in response.text


class TestSettingsIsolation:
    def test_cache_dir_fixture_overrides_defaults(self, cache_dir: Path) -> None:
        assert Settings().model_cache_dir == cache_dir
