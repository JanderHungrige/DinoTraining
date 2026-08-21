"""`POST /api/v1/generate/foundation` (doc 42).

The point of this endpoint is that a first-time user gets useful boxes before they have
labelled or trained anything. So the tests are about it behaving like the *expert* route in
every way a reviewer could notice — same response shape, same status codes — and differing
only in what it says produced the box.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

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


async def _post(client: AsyncClient, **body: object) -> object:
    return await client.post("/api/v1/generate/foundation", json=body)


class TestItRefusesWhatItCannotDo:
    async def test_an_uninstalled_model_is_a_409(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        # 409, not 404: the model exists and the fix is to download it. A 404 would send
        # the user looking for a name they typed correctly.
        response = await _post(
            client, image_path=_image(tmp_path), foundation_id="rf-detr-nano"
        )
        assert response.status_code == 409  # type: ignore[attr-defined]
        assert "Admin" in response.text  # type: ignore[attr-defined]

    async def test_a_depth_model_cannot_annotate_and_says_where_it_can_run(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        """A depth model is perfectly usable — just not as boxes. The error points at the
        tab where looking *is* the point, rather than only refusing."""
        response = await _post(
            client, image_path=_image(tmp_path), foundation_id="depth-anything-v2-small"
        )
        assert response.status_code == 409  # type: ignore[attr-defined]
        assert "Inference Viewer" in response.text  # type: ignore[attr-defined]

    async def test_an_unknown_model_is_a_404(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        response = await _post(
            client, image_path=_image(tmp_path), foundation_id="no-such-model"
        )
        assert response.status_code == 404  # type: ignore[attr-defined]

    async def test_a_missing_image_is_a_404_not_a_500(self, client: AsyncClient) -> None:
        # `FileNotFoundError` is an OSError and slips past both the LookupError clause and
        # the ValueError backstop — doc 36 shipped that bug once already.
        response = await _post(
            client, image_path="/nope/absent.jpg", foundation_id="rf-detr-nano"
        )
        assert response.status_code == 404  # type: ignore[attr-defined]

    async def test_an_unreadable_image_is_a_415(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        broken = tmp_path / "not-an-image.jpg"
        broken.write_text("plain text")
        response = await _post(
            client, image_path=str(broken), foundation_id="rf-detr-nano"
        )
        assert response.status_code == 415  # type: ignore[attr-defined]

    async def test_an_out_of_range_threshold_is_rejected(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        response = await _post(
            client,
            image_path=_image(tmp_path),
            foundation_id="rf-detr-nano",
            score_threshold=1.5,
        )
        assert response.status_code == 422  # type: ignore[attr-defined]


class TestItMatchesTheExpertRoute:
    async def test_both_routes_report_a_missing_image_the_same_way(
        self, client: AsyncClient
    ) -> None:
        """The review surface consumes one shape from two sources; the *failures* should
        agree too, or the UI needs a second error vocabulary for no reason."""
        foundation = await _post(
            client, image_path="/nope/absent.jpg", foundation_id="rf-detr-nano"
        )
        expert = await client.post(
            "/api/v1/generate/expert",
            json={
                "image_path": "/nope/absent.jpg",
                "backbone_id": "dinov2-small",
                "instance_id": "whatever",
            },
        )
        assert foundation.status_code == expert.status_code == 404  # type: ignore[attr-defined]
