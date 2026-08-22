"""`POST /api/v1/datasets/import/coco`.

Every failure here is bad input, so the point of this module is that none of them arrive as
a 500 with the only explanation in the log — the project's API rule, and the reason the
handler keeps a `ValueError -> 422` backstop below its specific clauses.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from PIL import Image

from app.datasets.coco_import import COCO_FILENAME
from tests.datasets_api_testkit import dataset_client


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for ac in dataset_client(tmp_path / "data", monkeypatch):
        yield ac


def _export(root: Path, *, splits: tuple[str, ...] = ("train",)) -> Path:
    """A minimal two-class COCO export, one image per split."""
    payload: dict[str, Any] = {
        "info": {},
        "licenses": [],
        "categories": [
            {"id": 0, "name": "thermal-dogs-n-people", "supercategory": "none"},
            {"id": 1, "name": "dog", "supercategory": "thermal-dogs-n-people"},
            {"id": 2, "name": "person", "supercategory": "thermal-dogs-n-people"},
        ],
        "images": [{"id": 0, "file_name": "a.jpg", "width": 40, "height": 30}],
        "annotations": [
            {"id": 1, "image_id": 0, "category_id": 1, "bbox": [1, 2, 10, 8]},
            {"id": 2, "image_id": 0, "category_id": 2, "bbox": [20, 4, 6, 12]},
        ],
    }
    for split in splits:
        directory = root / split
        directory.mkdir(parents=True, exist_ok=True)
        (directory / COCO_FILENAME).write_text(json.dumps(payload))
        Image.new("RGB", (40, 30), (10, 20, 30)).save(directory / "a.jpg")
    return root


class TestImporting:
    async def test_it_creates_a_dataset_and_reports_what_landed(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        directory = _export(tmp_path / "export", splits=("train", "valid"))
        response = await client.post(
            "/api/v1/datasets/import/coco",
            json={"name": "Thermal", "directory": str(directory)},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["images"] == 2
        assert body["boxes"] == 4
        assert body["class_names"] == ["dog", "person"]
        assert body["sources"] == ["train", "valid"]
        assert body["skipped_images"] == 0 and body["skipped_boxes"] == 0

    async def test_the_dataset_is_then_an_ordinary_dataset(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        # The whole design rests on this: nothing downstream should be able to tell an
        # imported dataset from a hand-annotated one, apart from its provenance.
        directory = _export(tmp_path / "export")
        created = await client.post(
            "/api/v1/datasets/import/coco",
            json={"name": "Thermal", "directory": str(directory)},
        )
        dataset_id = created.json()["dataset_id"]

        listed = await client.get(f"/api/v1/datasets/{dataset_id}")
        assert listed.status_code == 200
        assert listed.json()["counts"]["boxes"] == 2

        exported = await client.post(f"/api/v1/datasets/{dataset_id}/export/coco")
        assert exported.status_code == 200
        assert exported.json()["annotations"] == 2

    async def test_copy_images_brings_the_files_along(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        directory = _export(tmp_path / "export")
        response = await client.post(
            "/api/v1/datasets/import/coco",
            json={"name": "Thermal", "directory": str(directory), "copy_images": True},
        )
        dataset_id = response.json()["dataset_id"]
        counts = await client.get(f"/api/v1/datasets/{dataset_id}/counts")
        assert counts.json()["images"] == 1


class TestBadInputIsA422:
    async def test_a_directory_that_does_not_exist(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/datasets/import/coco",
            json={"name": "Nope", "directory": "/definitely/not/here"},
        )
        assert response.status_code == 422
        assert "Not a folder" in response.text

    async def test_a_directory_with_no_annotation_file(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        response = await client.post(
            "/api/v1/datasets/import/coco",
            json={"name": "Nope", "directory": str(empty)},
        )
        assert response.status_code == 422
        assert COCO_FILENAME in response.text

    async def test_malformed_json(self, client: AsyncClient, tmp_path: Path) -> None:
        directory = tmp_path / "broken" / "train"
        directory.mkdir(parents=True)
        (directory / COCO_FILENAME).write_text("{ not json")
        response = await client.post(
            "/api/v1/datasets/import/coco",
            json={"name": "Nope", "directory": str(tmp_path / "broken")},
        )
        assert response.status_code == 422

    async def test_an_empty_name_is_rejected_by_the_model(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/datasets/import/coco", json={"name": "", "directory": "/tmp"}
        )
        assert response.status_code == 422
