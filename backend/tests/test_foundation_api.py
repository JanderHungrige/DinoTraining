"""`GET /api/v1/foundation` and `POST /api/v1/foundation/predict`.

The listing must be honest about what is installed and what it costs to use, and the run
endpoint must not turn "you have not downloaded it" into "no such thing" — those are
different problems with different fixes, and `ModelNotInstalledError` subclasses
`LookupError`, so the ordering is the whole test.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.config import get_settings
from app.main import create_app
from app.ml.foundation.build import reset_cache


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_cache()

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    get_settings.cache_clear()
    reset_cache()


def _image(tmp_path: Path) -> str:
    path = tmp_path / "scene.jpg"
    Image.new("RGB", (40, 30), (10, 20, 30)).save(path)
    return str(path)


async def _listing(client: AsyncClient) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/foundation")
    assert response.status_code == 200
    return list(response.json()["foundations"])


class TestListing:
    async def test_it_offers_the_depth_models(self, client: AsyncClient) -> None:
        ids = {entry["id"] for entry in await _listing(client)}
        assert "depth-anything-v2-small" in ids

    async def test_nothing_is_installed_in_a_fresh_cache(self, client: AsyncClient) -> None:
        assert all(entry["installed"] is False for entry in await _listing(client))

    async def test_every_entry_states_its_licence(self, client: AsyncClient) -> None:
        # Surfaced in the viewer too, not only in the admin panel: this is where a user
        # meets a model they already installed, and "may I use this output?" is asked here.
        assert all(entry["licence"].strip() for entry in await _listing(client))

    async def test_the_non_commercial_variants_are_flagged(self, client: AsyncClient) -> None:
        by_id = {entry["id"]: entry for entry in await _listing(client)}
        assert by_id["depth-anything-v2-small"]["non_commercial"] is False
        assert by_id["depth-anything-v2-base"]["non_commercial"] is True
        assert by_id["depth-anything-v2-large"]["non_commercial"] is True

    async def test_it_carries_the_render_hint_the_viewer_dispatches_on(
        self, client: AsyncClient
    ) -> None:
        assert all(entry["render_hint"] == "depth-map" for entry in await _listing(client))

    async def test_it_states_the_download_size(self, client: AsyncClient) -> None:
        assert all(entry["approx_size_mb"] > 0 for entry in await _listing(client))


class TestRunning:
    async def test_a_model_that_is_not_downloaded_is_a_409(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        # 409, not 404. The thing exists and the fix is "download it" — reporting 404
        # would send the user looking for a name they typed correctly.
        response = await client.post(
            "/api/v1/foundation/predict",
            json={"image_path": _image(tmp_path), "foundation_id": "depth-anything-v2-small"},
        )
        assert response.status_code == 409
        assert "Admin" in response.text

    async def test_an_unknown_model_is_a_404(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        response = await client.post(
            "/api/v1/foundation/predict",
            json={"image_path": _image(tmp_path), "foundation_id": "no-such-model"},
        )
        assert response.status_code == 404

    async def test_an_unreadable_image_is_a_415(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        broken = tmp_path / "not-an-image.jpg"
        broken.write_text("plain text")
        response = await client.post(
            "/api/v1/foundation/predict",
            json={"image_path": str(broken), "foundation_id": "depth-anything-v2-small"},
        )
        assert response.status_code == 415

    async def test_a_missing_image_is_a_404_and_never_a_500(
        self, client: AsyncClient
    ) -> None:
        """The first version of this handler returned 500 here.

        `FileNotFoundError` is an `OSError`, so it slipped past both the `LookupError`
        clause and the `ValueError` backstop that were meant to make a 500 impossible —
        the project rule holds only for the exception hierarchies it actually names.
        """
        response = await client.post(
            "/api/v1/foundation/predict",
            json={"image_path": "/nope/absent.jpg", "foundation_id": "depth-anything-v2-small"},
        )
        assert response.status_code == 404

    async def test_an_empty_id_is_rejected_by_the_model(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/foundation/predict",
            json={"image_path": "/x.jpg", "foundation_id": ""},
        )
        assert response.status_code == 422
