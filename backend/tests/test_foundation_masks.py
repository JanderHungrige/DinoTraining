"""The mask half of a foundation proposal, through the real ASGI app (doc 61).

Until doc 61 the Studio's proposal route ran the whole Grounded SAM pipeline and returned
only the boxes — the segmentation was computed and dropped on every run. These tests pin
the two halves arriving together, and pin the detector case staying `null` so nothing
downstream has to ask which model produced the response.
"""

from __future__ import annotations

import base64
import io
from collections.abc import AsyncGenerator
from pathlib import Path

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.config import get_settings
from app.datasets.rle import rle_encode
from app.main import create_app
from app.ml.annotators.base import MaskProposal
from app.ml.foundation.concept import ConceptSegmenter
from app.ml.foundation.registry import get_foundation

WIDTH, HEIGHT = 60, 40


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    get_settings.cache_clear()


@pytest.fixture
def image_path(tmp_path: Path) -> str:
    path = tmp_path / "frame.png"
    Image.new("RGB", (WIDTH, HEIGHT), "grey").save(path)
    return str(path)


def _rle(box: tuple[int, int, int, int]) -> list[int]:
    x, y, w, h = box
    array = np.zeros((HEIGHT, WIDTH), dtype=bool)
    array[y : y + h, x : x + w] = True
    return rle_encode(array)[0]


def _proposal(concept: str, box: tuple[int, int, int, int]) -> MaskProposal:
    return MaskProposal(
        counts=_rle(box),
        size=(HEIGHT, WIDTH),
        box=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
        score=0.9,
        concept=concept,
    )


class _StubAnnotator:
    annotator_id = "grounded-sam"

    def __init__(self, proposals: list[MaskProposal]) -> None:
        self._proposals = proposals

    def propose(
        self, image: Image.Image, concept: str, *, threshold: float = 0.3
    ) -> list[MaskProposal]:
        return self._proposals


@pytest.fixture
def segmenting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the foundation builder at a stubbed Grounded SAM."""
    spec = get_foundation("grounded-sam")
    assert spec is not None
    stub = _StubAnnotator([_proposal("cat", (5, 5, 10, 10)), _proposal("dog", (30, 20, 12, 8))])
    monkeypatch.setattr("app.ml.foundation.concept.build_annotator", lambda _id: stub)
    monkeypatch.setattr(
        "app.ml.annotators.foundation.build_foundation",
        lambda *a, **k: ConceptSegmenter(spec),
    )


def decode_png(encoded: str) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(base64.b64decode(encoded))))


async def propose(client: AsyncClient, image_path: str, **over: object) -> dict:
    response = await client.post(
        "/api/v1/generate/foundation",
        json={
            "image_path": image_path,
            "foundation_id": "grounded-sam",
            "concept": "cat. dog.",
            **over,
        },
    )
    assert response.status_code == 200, response.text
    body: dict = response.json()
    return body


@pytest.mark.usefixtures("segmenting")
class TestAConceptSegmenter:
    async def test_every_proposal_carries_its_mask(
        self, client: AsyncClient, image_path: str
    ) -> None:
        body = await propose(client, image_path)

        assert len(body["boxes"]) == 2
        assert all(entry["mask"] is not None for entry in body["boxes"])

    async def test_the_box_is_unchanged_beside_it(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # The box half is what doc 42 shipped and what the review list still shows. The
        # mask is an addition, not a replacement.
        body = await propose(client, image_path)

        first = body["boxes"][0]["box"]
        assert (first["x"], first["y"], first["w"], first["h"]) == (5.0, 5.0, 10.0, 10.0)
        assert first["prompt"] == "cat"
        assert first["provenance"] == "foundation-model"

    async def test_the_rle_covers_the_frame_not_the_box(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # A mask clamped to its own bounding box would be a rectangle — which is exactly
        # the information the box already carried.
        body = await propose(client, image_path)

        assert body["boxes"][0]["mask"]["rle"]["size"] == [HEIGHT, WIDTH]

    async def test_the_preview_is_a_zero_or_255_png_of_the_right_size(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # 0/1 would render as an invisible mask — every pixel effectively black.
        body = await propose(client, image_path)

        pixels = decode_png(body["boxes"][0]["mask"]["png"])
        assert pixels.shape == (HEIGHT, WIDTH)
        assert set(np.unique(pixels).tolist()) == {0, 255}

    async def test_the_preview_matches_the_rle(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # The drawn thing and the stored thing must be the same shape, or the reviewer
        # accepts one mask and the dataset keeps another.
        body = await propose(client, image_path)

        pixels = decode_png(body["boxes"][0]["mask"]["png"])
        ys, xs = (pixels > 0).nonzero()
        assert (int(xs.min()), int(ys.min())) == (5, 5)
        assert (int(xs.max()), int(ys.max())) == (14, 14)

    async def test_an_empty_concept_is_refused(
        self, client: AsyncClient, image_path: str
    ) -> None:
        # Nothing-found and nothing-asked look identical on a canvas.
        response = await client.post(
            "/api/v1/generate/foundation",
            json={
                "image_path": image_path,
                "foundation_id": "grounded-sam",
                "concept": "   ",
            },
        )
        assert response.status_code == 409
