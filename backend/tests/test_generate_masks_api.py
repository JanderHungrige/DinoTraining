"""Tests for POST /generate/masks — the mask-proposal endpoint.

Status codes carry most of the meaning here, and three of them are easy to get wrong:
a catalogued-but-unbuilt annotator is not a 404, a missing download is not a 404, and an
unknown id is not a 500.
"""

from __future__ import annotations

import base64
import io
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.main import create_app
from app.ml.annotators.base import MaskProposal


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_connection()
    with TestClient(create_app()) as c:
        yield c
    reset_connection()
    get_settings.cache_clear()


def write_image(path: Path, size: tuple[int, int] = (40, 30)) -> str:
    Image.new("RGB", size, (100, 100, 100)).save(path)
    return str(path)


def proposal(x0: int = 5, y0: int = 5, x1: int = 15, y1: int = 20) -> MaskProposal:
    from app.datasets.rle import rle_encode

    mask = np.zeros((30, 40), dtype=bool)
    mask[y0:y1, x0:x1] = True
    counts, size = rle_encode(mask)
    return MaskProposal(
        counts=counts,
        size=size,
        box=(float(x0), float(y0), float(x1 - x0), float(y1 - y0)),
        score=0.85,
        concept="bolt",
    )


class _StubAnnotator:
    annotator_id = "grounded-sam"

    def __init__(self, proposals: list[MaskProposal]) -> None:
        self._proposals = proposals

    def propose(self, image, concept, *, threshold=0.3):  # noqa: ANN001, ANN204
        return self._proposals


def stub_annotator(monkeypatch: pytest.MonkeyPatch, proposals: list[MaskProposal]) -> None:
    monkeypatch.setattr(
        "app.api.v1.generate.build_annotator", lambda _id: _StubAnnotator(proposals)
    )


class TestProposeMasks:
    def test_it_returns_a_mask(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub_annotator(monkeypatch, [proposal()])
        image = write_image(tmp_path / "a.png")

        response = client.post(
            "/api/v1/generate/masks", json={"image_path": image, "concept": "a bolt"}
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["masks"]) == 1
        assert body["annotator_id"] == "grounded-sam"

    def test_masks_are_marked_as_coming_from_grounded_sam(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Not `sam3`: a different pipeline under a different licence."""
        stub_annotator(monkeypatch, [proposal()])
        image = write_image(tmp_path / "a.png")

        body = client.post(
            "/api/v1/generate/masks", json={"image_path": image, "concept": "a bolt"}
        ).json()
        assert body["masks"][0]["provenance"] == "grounded-sam"

    def test_the_rle_is_storable_as_submitted(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The proposal must be acceptable to PUT .../images/masks without reshaping."""
        stub_annotator(monkeypatch, [proposal()])
        image = write_image(tmp_path / "a.png")

        proposed = client.post(
            "/api/v1/generate/masks", json={"image_path": image, "concept": "a bolt"}
        ).json()

        dataset = client.post("/api/v1/datasets", json={"name": "Generated"}).json()
        saved = client.put(
            f"/api/v1/datasets/{dataset['id']}/images/masks",
            json={
                "path": proposed["image_path"],
                "width": proposed["width"],
                "height": proposed["height"],
                "masks": [
                    {
                        "label": m["label"],
                        "provenance": m["provenance"],
                        "rle": m["rle"],
                        "prompt": m["concept"],
                        "score": m["score"],
                    }
                    for m in proposed["masks"]
                ],
            },
        )

        assert saved.status_code == 200, saved.text
        assert saved.json()["masks"] == 1

    def test_the_preview_png_decodes_to_the_same_mask(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The preview and the stored RLE must describe the same pixels."""
        from app.datasets.rle import rle_decode

        stub_annotator(monkeypatch, [proposal()])
        image = write_image(tmp_path / "a.png")

        mask_body = client.post(
            "/api/v1/generate/masks", json={"image_path": image, "concept": "a bolt"}
        ).json()["masks"][0]

        png = Image.open(io.BytesIO(base64.b64decode(mask_body["mask_png"])))
        preview = np.array(png) > 0
        stored = rle_decode(mask_body["rle"]["counts"], tuple(mask_body["rle"]["size"]))

        assert np.array_equal(preview, stored)

    def test_the_bounding_box_is_reported_so_no_client_decodes_an_rle(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub_annotator(monkeypatch, [proposal(5, 5, 15, 20)])
        image = write_image(tmp_path / "a.png")

        mask_body = client.post(
            "/api/v1/generate/masks", json={"image_path": image, "concept": "a bolt"}
        ).json()["masks"][0]

        assert (mask_body["x"], mask_body["y"], mask_body["w"], mask_body["h"]) == (
            5.0,
            5.0,
            10.0,
            15.0,
        )

    def test_finding_nothing_is_an_empty_list_not_an_error(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub_annotator(monkeypatch, [])
        image = write_image(tmp_path / "a.png")

        response = client.post(
            "/api/v1/generate/masks", json={"image_path": image, "concept": "a unicorn"}
        )
        assert response.status_code == 200
        assert response.json()["masks"] == []


class TestErrors:
    def test_an_unknown_annotator_is_404(self, client: TestClient, tmp_path: Path) -> None:
        image = write_image(tmp_path / "a.png")
        response = client.post(
            "/api/v1/generate/masks",
            json={"image_path": image, "concept": "x", "annotator_id": "nope"},
        )
        assert response.status_code == 404

    def test_a_catalogued_but_unbuilt_annotator_is_501_not_404(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A real, listed id that cannot run yet must not read as "no such thing".

        Both catalogue entries are implemented now, so the unbuilt case is simulated —
        but the mapping still has to hold for the next annotator added.
        """
        from app.ml.annotators.build import AnnotatorUnavailableError

        def unavailable(_id: str) -> None:
            raise AnnotatorUnavailableError("not built yet")

        monkeypatch.setattr("app.api.v1.generate.build_annotator", unavailable)
        image = write_image(tmp_path / "a.png")

        response = client.post(
            "/api/v1/generate/masks",
            json={"image_path": image, "concept": "x", "annotator_id": "sam3"},
        )
        assert response.status_code == 501

    def test_sam3_without_its_weights_is_409_not_501(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Implemented but not downloaded is a different answer from not implemented."""
        image = write_image(tmp_path / "a.png")
        response = client.post(
            "/api/v1/generate/masks",
            json={"image_path": image, "concept": "a bolt", "annotator_id": "sam3"},
        )
        assert response.status_code == 409
        assert "Admin tab" in response.json()["error"]["message"]

    def test_a_missing_model_is_409_with_what_to_download(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Nothing is installed in this fixture's cache, so the real builder is used."""
        image = write_image(tmp_path / "a.png")
        response = client.post(
            "/api/v1/generate/masks", json={"image_path": image, "concept": "a bolt"}
        )
        assert response.status_code == 409
        message = response.json()["error"]["message"]
        assert "Admin tab" in message
        assert "grounding-dino-tiny" in message

    def test_a_missing_image_is_404(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/generate/masks", json={"image_path": "/nope.png", "concept": "x"}
        )
        assert response.status_code == 404

    def test_a_non_image_is_415(self, client: TestClient, tmp_path: Path) -> None:
        junk = tmp_path / "notes.txt"
        junk.write_text("not an image")
        response = client.post(
            "/api/v1/generate/masks", json={"image_path": str(junk), "concept": "x"}
        )
        assert response.status_code == 415

    def test_an_empty_concept_is_422(self, client: TestClient, tmp_path: Path) -> None:
        image = write_image(tmp_path / "a.png")
        response = client.post(
            "/api/v1/generate/masks", json={"image_path": image, "concept": ""}
        )
        assert response.status_code == 422
