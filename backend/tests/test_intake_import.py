"""Doc 136: importing every format, the parameters, and the API around it."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.datasets.db import transaction
from app.datasets.intake.importer import run_import
from app.datasets.intake.profile import dataset_profile
from app.datasets.masks import MaskStore
from app.datasets.store import MANIFEST_NAME, DatasetStore, dataset_dir
from tests import intake_fixtures as fx


@pytest.fixture(autouse=True)
def _data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.datasets.db import reset_connection

    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_connection()


def _annotated_flags(dataset_id: str) -> list[bool]:
    with transaction() as connection:
        rows = connection.execute(
            "SELECT annotated_at != '' AS done FROM images WHERE dataset_id = ? ORDER BY path",
            (dataset_id,),
        ).fetchall()
    return [bool(row["done"]) for row in rows]


def test_coco_with_masks_splits_and_an_unannotated_extra(tmp_path: Path) -> None:
    result = run_import(fx.coco(tmp_path / "set"), "Rail", "Signals near Hamburg", False)
    assert (result.pictures, result.annotated_pictures, result.objects) == (4, 3, 3)
    assert result.masks == 2  # one polygon, one compressed RLE
    profile = dataset_profile(result.dataset_id)
    assert profile.pictures == 4 and profile.annotated_pictures == 3
    assert profile.annotation_types == ["boxes", "masks"]
    assert profile.classes == ["person", "signal"]
    assert profile.media == "images" and profile.description == "Signals near Hamburg"
    assert sorted(_annotated_flags(result.dataset_id)) == [False, True, True, True]
    stored = [mask for *_row, masks in MaskStore().image_masks(result.dataset_id) for mask in masks]
    assert len(stored) == 2
    assert {mask.provenance for mask in stored} == {"imported"}


def test_yolo_and_voc_and_openlabel(tmp_path: Path) -> None:
    yolo = run_import(fx.yolo(tmp_path / "y"), "", None, False)
    assert yolo.name == "y" and (yolo.pictures, yolo.annotated_pictures) == (3, 3)
    assert yolo.objects == 3 and yolo.masks == 1 and yolo.classes == ["car", "person"]
    voc = run_import(fx.voc(tmp_path / "v"), "VOC", None, True)
    assert voc.objects == 1 and voc.classes == ["dog"]
    rail = run_import(fx.openlabel(tmp_path / "o"), "OSDaR", None, False)
    assert rail.annotated_pictures == 2 and rail.classes == ["person"]


def test_pictures_only_are_in_the_dataset_but_not_annotated(tmp_path: Path) -> None:
    result = run_import(fx.pictures_only(tmp_path / "p"), "Raw", None, False)
    assert result.pictures == 3 and result.annotated_pictures == 0
    assert _annotated_flags(result.dataset_id) == [False, False, False]
    profile = dataset_profile(result.dataset_id)
    assert profile.annotation_types == [] and profile.classes == []


def test_a_video_becomes_one_sequence_of_frames(tmp_path: Path) -> None:
    clip = fx.video(tmp_path / "clip.mp4", frames=12)
    result = run_import(clip, "Ride", None, False)
    profile = dataset_profile(result.dataset_id)
    assert profile.media == "video" and profile.sequences == 1
    assert profile.pictures == result.pictures and result.pictures >= 10
    assert profile.annotated_pictures == 0


def test_the_manifest_records_description_source_and_what_arrived(tmp_path: Path) -> None:
    folder = fx.voc(tmp_path / "v")
    result = run_import(folder, "VOC", "  dogs  ", False)
    manifest = json.loads((dataset_dir(result.dataset_id) / MANIFEST_NAME).read_text())
    assert manifest["description"] == "dogs" and manifest["source"] == str(folder)
    assert manifest["imported"]["kind"] == "voc" and manifest["imported"]["classes"] == ["dog"]
    info = DatasetStore().get(result.dataset_id)
    assert info.description == "dogs" and info.source == str(folder)


def test_a_failed_import_leaves_no_half_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.datasets.intake import importer

    def broken(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(importer, "set_details", broken)
    with pytest.raises(RuntimeError):
        run_import(fx.voc(tmp_path / "v"), "VOC", None, False)
    assert DatasetStore().list_all() == []


def test_the_api_detects_imports_in_the_background_and_profiles(tmp_path: Path) -> None:
    from app.main import create_app

    client = TestClient(create_app())
    folder = fx.yolo(tmp_path / "y")
    detected = client.post("/api/v1/datasets/import/detect", json={"path": str(folder)})
    assert detected.status_code == 200 and detected.json()["kind"] == "yolo"
    assert (
        client.post(
            "/api/v1/datasets/import/detect", json={"path": str(tmp_path / "nope")}
        ).status_code
        == 422
    )

    started = client.post("/api/v1/datasets/import", json={"path": str(folder), "name": "Cars"})
    assert started.status_code == 202
    job_id = started.json()["job_id"]
    for _ in range(100):
        job = client.get(f"/api/v1/datasets/import/jobs/{job_id}").json()
        if job["state"] != "running":
            break
        time.sleep(0.05)
    assert job["state"] == "complete", job
    dataset_id = job["result"]["dataset_id"]
    profile = client.get(f"/api/v1/datasets/{dataset_id}/profile").json()
    assert profile["pictures"] == 3 and profile["classes"] == ["car", "person"]
    assert client.get("/api/v1/datasets/nope/profile").status_code == 404
    listed = client.get("/api/v1/datasets/profiles").json()["profiles"]
    assert [entry["dataset_id"] for entry in listed] == [dataset_id]
    assert client.get("/api/v1/datasets/import/jobs/nope").status_code == 404


def test_never_annotated_pictures_stay_out_of_training_until_saved(tmp_path: Path) -> None:
    """Found building doc 136: head training reads a picture without boxes as pure
    background. An imported picture nobody has looked at must not teach "nothing here"."""
    from app.datasets.completeness import unknown_pictures
    from app.datasets.models import Box, ImageAnnotation
    from app.ml.training.sample_prep import load_preparation

    result = run_import(fx.pictures_only(tmp_path / "p"), "Raw", None, False)
    store = DatasetStore()
    rows = store.image_annotations(result.dataset_id)
    assert {row[0] for row in rows} == load_preparation(result.dataset_id).excluded

    first = rows[0]
    store.replace_image_boxes(
        result.dataset_id,
        ImageAnnotation(
            path=first[1],
            width=first[2],
            height=first[3],
            boxes=[
                Box(label="positive", provenance="hand-drawn", x=1, y=1, w=5, h=5, prompt="cat")
            ],
        ),
    )
    assert first[0] not in load_preparation(result.dataset_id).excluded
    assert len(load_preparation(result.dataset_id).excluded) == 2
    with transaction() as connection:
        # Not "saved before the class existed" either (doc 118's banner stays quiet).
        assert unknown_pictures(connection, result.dataset_id, "cat") == []


def test_the_export_leaves_never_annotated_pictures_out(tmp_path: Path) -> None:
    from app.main import create_app

    result = run_import(fx.coco(tmp_path / "set"), "Rail", None, False)
    client = TestClient(create_app())
    exported = client.post(f"/api/v1/datasets/{result.dataset_id}/export/coco").json()
    assert exported["images"] == 3  # extra.jpg, in no annotation file, is not "empty"
