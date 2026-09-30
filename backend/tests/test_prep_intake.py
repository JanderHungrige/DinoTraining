"""Checking a published export before import, and importing what was checked (doc 82)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.datasets.db import transaction
from app.main import create_app
from app.prep.intake import inspect_coco

W, H = 200, 100


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def export(
    root: Path,
    boxes: list[list[float]],
    names: tuple[str, ...] = ("car",),
    folders: tuple[str, ...] = ("train", "valid"),
    declared: tuple[int, int] = (W, H),
    missing: bool = False,
) -> Path:
    """A Roboflow-shaped export: one folder per split, images beside the annotation file."""
    for folder in folders:
        directory = root / folder
        directory.mkdir(parents=True)
        images, annotations = [], []
        for index, bbox in enumerate(boxes):
            name = f"{folder}{index}.jpg"
            if not (missing and index == 0):
                Image.new("RGB", (W, H), (index * 20, 50, 90)).save(directory / name)
            images.append(
                {"id": index, "file_name": name, "width": declared[0], "height": declared[1]}
            )
            category = 1 + index % len(names)
            annotations.append(
                {"id": index, "image_id": index, "category_id": category, "bbox": bbox}
            )
        categories = [{"id": i + 1, "name": n} for i, n in enumerate(names)]
        payload = {"images": images, "annotations": annotations, "categories": categories}
        (directory / "_annotations.coco.json").write_text(json.dumps(payload))
    return root


def test_a_standard_export_needs_no_conversion(tmp_path: Path) -> None:
    report = inspect_coco(export(tmp_path, [[10, 10, 50, 40]] * 6))
    assert report.convention == "xywh"
    assert report.has_source_split
    assert [f.split for f in report.files] == ["train", "val"]
    ids = {f.id for f in report.findings}
    assert "box-convention-converted" not in ids
    assert "source-split" in ids


def test_corner_coordinates_are_recognised_from_the_evidence(tmp_path: Path) -> None:
    # x1,y1,x2,y2 boxes: read as x,y,w,h, most of them run off the right-hand edge.
    corners = [[120, 20, 190, 80], [100, 10, 180, 90], [60, 5, 150, 60], [150, 50, 199, 99]]
    report = inspect_coco(export(tmp_path, corners))
    assert report.files[0].evidence.valid_as_xyxy == 1.0
    assert report.files[0].evidence.valid_as_xywh < 0.9
    assert report.convention == "xyxy"
    assert {f.id for f in report.findings} >= {"box-convention-converted"}


def test_normalised_boxes_are_recognised(tmp_path: Path) -> None:
    report = inspect_coco(export(tmp_path, [[0.1, 0.2, 0.3, 0.4]] * 3))
    assert report.convention == "xywh-normalized"


def test_mixed_evidence_is_called_unclear_not_guessed(tmp_path: Path) -> None:
    # Half fit only one reading, half fit neither: no convention explains this file.
    boxes = [[10, 10, 50, 40], [120, 20, 190, 80], [150, 60, 100, 90], [180, 70, 150, 90]]
    report = inspect_coco(export(tmp_path, boxes, folders=("train",)))
    assert report.convention is None
    assert report.findings[0].id == "box-convention-unclear"
    assert report.findings[0].severity == "problem"


def test_spellings_of_one_class_are_proposed_for_merging(tmp_path: Path) -> None:
    report = inspect_coco(
        export(tmp_path, [[1, 1, 5, 5]] * 5, names=("traffic-light", "Traffic Lights"))
    )
    # The most-used spelling wins; merges are proposals, applied only on import.
    assert report.proposed_class_map == {"traffic lights": "traffic-light"}


def test_missing_images_and_wrong_sizes_are_findings(tmp_path: Path) -> None:
    report = inspect_coco(
        export(tmp_path, [[1, 1, 5, 5]] * 4, folders=("train",), declared=(400, 200), missing=True)
    )
    found = {f.id: f for f in report.findings}
    assert found["missing-images"].examples == ["train0.jpg"]
    assert found["size-mismatch"].metrics["count"] == 3


def _stored(dataset_id: str) -> list[tuple[str, float, float, str | None]]:
    with transaction() as connection:
        rows = connection.execute(
            "SELECT b.prompt, b.w, b.h, i.split FROM boxes b JOIN images i ON i.id = b.image_id"
            " WHERE i.dataset_id = ? ORDER BY i.id",
            (dataset_id,),
        ).fetchall()
    return [(r["prompt"], r["w"], r["h"], r["split"]) for r in rows]


def test_importing_as_checked_converts_merges_and_keeps_the_split(
    client: TestClient, tmp_path: Path
) -> None:
    directory = export(tmp_path / "ex", [[120, 20, 190, 80]] * 2, names=("Cars", "car"))
    report = client.post("/api/v1/datasets/import/coco/inspect", json={"directory": str(directory)})
    assert report.status_code == 200
    checked = report.json()
    body = {
        "name": "Checked",
        "directory": str(directory),
        "box_convention": checked["convention"],
        "class_map": checked["proposed_class_map"],
        "keep_source_split": True,
    }
    imported = client.post("/api/v1/datasets/import/coco", json=body).json()
    assert imported["skipped_boxes"] == 0
    stored = _stored(imported["dataset_id"])
    # One class, under whichever spelling the proposal chose.
    assert len({name for name, *_ in stored}) == 1
    assert {name for name, *_ in stored} <= set(checked["proposed_class_map"].values())
    assert {(w, h) for _, w, h, _ in stored} == {(70.0, 60.0)}
    assert sorted({split for *_, split in stored}) == ["train", "val"]


def test_importing_corners_unconverted_loses_them_which_is_why_intake_exists(
    client: TestClient, tmp_path: Path
) -> None:
    directory = export(tmp_path / "ex", [[120, 20, 190, 80]] * 2, folders=("train",))
    body = {"name": "Unchecked", "directory": str(directory)}
    imported = client.post("/api/v1/datasets/import/coco", json=body).json()
    assert imported["skipped_boxes"] == 2


def test_inspecting_a_folder_without_an_export_is_a_422(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/datasets/import/coco/inspect", json={"directory": str(tmp_path)}
    )
    assert response.status_code == 422
