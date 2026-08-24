"""Tests for GET /api/v1/health — the readiness contract the Tauri shell polls."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    async def test_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_response_shape_matches_documented_contract(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        body = response.json()
        assert set(body) == {"status", "version", "device", "api_prefix"}

    async def test_status_is_literal_ok(self, client: AsyncClient) -> None:
        """The shell treats anything other than "ok" as not-ready."""
        body = (await client.get("/api/v1/health")).json()
        assert body["status"] == "ok"

    async def test_device_is_concrete_never_auto(self, client: AsyncClient) -> None:
        body = (await client.get("/api/v1/health")).json()
        assert body["device"] in {"cuda", "mps", "cpu"}

    async def test_api_prefix_echoes_configuration(self, client: AsyncClient) -> None:
        body = (await client.get("/api/v1/health")).json()
        assert body["api_prefix"] == "/api/v1"

    async def test_version_is_non_empty(self, client: AsyncClient) -> None:
        body = (await client.get("/api/v1/health")).json()
        assert isinstance(body["version"], str)
        assert body["version"]

    async def test_health_leaks_no_token_or_path_information(self, client: AsyncClient) -> None:
        """Doc Security section: health exposes device and version only."""
        raw = (await client.get("/api/v1/health")).text.lower()
        for leak in ("hf_", "token", "/users/", "cache_dir", "data_dir"):
            assert leak not in raw

    async def test_unprefixed_health_is_not_routed(self, client: AsyncClient) -> None:
        """Every endpoint lives under /api/v1 — see CLAUDE.md."""
        assert (await client.get("/health")).status_code == 404


class TestExceptionHandling:
    async def test_unhandled_error_returns_shaped_json_without_traceback(self) -> None:
        app = create_app()

        @app.get("/api/v1/_boom")
        async def _boom() -> None:
            raise RuntimeError("internal detail that must not reach the client")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/_boom")

        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "internal_error"
        assert "internal detail" not in response.text
        assert "Traceback" not in response.text

    async def test_http_exception_keeps_its_status_and_is_shaped(self) -> None:
        app = create_app()

        @app.get("/api/v1/_missing")
        async def _missing() -> None:
            raise HTTPException(status_code=404, detail="no such thing")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/_missing")

        assert response.status_code == 404
        assert response.json()["error"]["message"] == "no such thing"
