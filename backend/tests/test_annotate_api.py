"""Tests for the annotate endpoints. The detector is patched — no weights involved."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.config import get_settings
from app.main import create_app
from app.ml.detector import Detection, Detector, ModelNotInstalledError


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def image(tmp_path: Path) -> Path:
    path = tmp_path / "pics" / "a.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (200, 150), (10, 90, 10)).save(path)
    return path


def fake_detector() -> Detector:
    return Detector(model_id="grounding-dino-tiny", device="cpu", processor=None, model=None)


def patch_detector(
    monkeypatch: pytest.MonkeyPatch, detections: list[Detection] | None = None
) -> None:
    monkeypatch.setattr("app.api.v1.annotate.load_detector", lambda model_id: fake_detector())
    monkeypatch.setattr(
        "app.api.v1.annotate.detect",
        lambda detector, image, prompt, box_t, text_t: detections or [],
    )


class TestAnnotate:
    async def test_returns_proposals_in_store_convention(
        self, client: AsyncClient, image: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_detector(monkeypatch, [Detection(x=10, y=20, w=30, h=40, score=0.9, text="a cat")])

        response = await client.post(
            "/api/v1/annotate", json={"image_path": str(image), "prompt": "a cat"}
        )

        assert response.status_code == 200
        body = response.json()
        assert (body["width"], body["height"]) == (200, 150)
        box = body["boxes"][0]
        assert (box["x"], box["y"], box["w"], box["h"]) == (10, 20, 30, 40)
        assert box["score"] == 0.9
        assert box["text"] == "a cat"

    async def test_proposals_are_labelled_positive_from_grounding_dino(
        self, client: AsyncClient, image: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The detector asserts presence; the user's job is to downgrade the wrong ones."""
        patch_detector(monkeypatch, [Detection(x=1, y=1, w=5, h=5, score=0.5, text="a cat")])

        body = (
            await client.post(
                "/api/v1/annotate", json={"image_path": str(image), "prompt": "a cat"}
            )
        ).json()

        assert body["boxes"][0]["label"] == "positive"
        assert body["boxes"][0]["provenance"] == "grounding-dino"

    async def test_a_proposal_is_directly_saveable_to_a_dataset(
        self, client: AsyncClient, image: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """No translation layer between propose and store — the shapes must match."""
        monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
        get_settings.cache_clear()
        from app.datasets.db import reset_connection

        reset_connection()
        patch_detector(monkeypatch, [Detection(x=10, y=20, w=30, h=40, score=0.9, text="a cat")])

        proposals = (
            await client.post(
                "/api/v1/annotate", json={"image_path": str(image), "prompt": "a cat"}
            )
        ).json()
        dataset = (await client.post("/api/v1/datasets", json={"name": "Cats"})).json()

        saved = await client.put(
            f"/api/v1/datasets/{dataset['id']}/images",
            json={
                "path": proposals["image_path"],
                "width": proposals["width"],
                "height": proposals["height"],
                "boxes": proposals["boxes"],
            },
        )

        assert saved.status_code == 200
        assert saved.json()["positive"] == 1
        reset_connection()

    async def test_no_detections_is_an_empty_list_not_an_error(
        self, client: AsyncClient, image: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_detector(monkeypatch, [])
        body = (
            await client.post(
                "/api/v1/annotate", json={"image_path": str(image), "prompt": "a unicorn"}
            )
        ).json()
        assert body["boxes"] == []

    async def test_missing_image_is_404(
        self, client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_detector(monkeypatch)
        response = await client.post(
            "/api/v1/annotate", json={"image_path": str(tmp_path / "gone.png"), "prompt": "a cat"}
        )
        assert response.status_code == 404

    async def test_non_image_file_is_400(
        self, client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_detector(monkeypatch)
        secret = tmp_path / "secrets.env"
        secret.write_text("HF_TOKEN=hf_supersecret")

        response = await client.post(
            "/api/v1/annotate", json={"image_path": str(secret), "prompt": "a cat"}
        )

        assert response.status_code == 400
        assert "hf_supersecret" not in response.text

    async def test_uninstalled_model_is_404_pointing_at_the_admin_tab(
        self, client: AsyncClient, image: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def not_installed(model_id: str) -> Any:
            raise ModelNotInstalledError(model_id)

        monkeypatch.setattr("app.api.v1.annotate.load_detector", not_installed)

        response = await client.post(
            "/api/v1/annotate", json={"image_path": str(image), "prompt": "a cat"}
        )

        assert response.status_code == 404
        assert "Admin tab" in response.json()["error"]["message"]

    async def test_blank_prompt_is_422(
        self, client: AsyncClient, image: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_detector(monkeypatch)
        response = await client.post(
            "/api/v1/annotate", json={"image_path": str(image), "prompt": ""}
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("threshold", [-0.1, 1.5])
    async def test_out_of_range_threshold_is_422(
        self,
        client: AsyncClient,
        image: Path,
        monkeypatch: pytest.MonkeyPatch,
        threshold: float,
    ) -> None:
        patch_detector(monkeypatch)
        response = await client.post(
            "/api/v1/annotate",
            json={"image_path": str(image), "prompt": "a cat", "box_threshold": threshold},
        )
        assert response.status_code == 422


class TestFolderListing:
    async def test_lists_images(self, client: AsyncClient, image: Path) -> None:
        body = (
            await client.get("/api/v1/annotate/folder", params={"path": str(image.parent)})
        ).json()
        assert body["images"] == [str(image)]

    async def test_missing_folder_is_404(self, client: AsyncClient, tmp_path: Path) -> None:
        response = await client.get(
            "/api/v1/annotate/folder", params={"path": str(tmp_path / "absent")}
        )
        assert response.status_code == 404

    async def test_excludes_non_images(self, client: AsyncClient, image: Path) -> None:
        (image.parent / "notes.txt").write_text("nope")
        body = (
            await client.get("/api/v1/annotate/folder", params={"path": str(image.parent)})
        ).json()
        assert len(body["images"]) == 1


class TestImageStreaming:
    async def test_streams_the_bytes(self, client: AsyncClient, image: Path) -> None:
        response = await client.get("/api/v1/annotate/image", params={"path": str(image)})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")

    async def test_refuses_a_non_image(self, client: AsyncClient, tmp_path: Path) -> None:
        secret = tmp_path / "secrets.env"
        secret.write_text("HF_TOKEN=hf_supersecret")

        response = await client.get("/api/v1/annotate/image", params={"path": str(secret)})

        assert response.status_code == 400
        assert "hf_supersecret" not in response.text
