"""The data-requirements contract and the preflight check (doc 92)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.finetune.requirements import REQUIREMENTS
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_connection()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_connection()
    get_settings.cache_clear()


def test_every_model_says_what_its_data_must_look_like() -> None:
    ids = {spec.id for spec in REQUIREMENTS}
    assert {"rf-detr-nano", "sam2.1-hiera-small", "sam3", "dinov3-vitb16-segmentation"} <= ids
    for spec in REQUIREMENTS:
        assert len(spec.data_format) > 80, spec.id  # a real explanation, not a label
        assert spec.minimums_why and spec.what_trains, spec.id
        assert spec.available or spec.unavailable_reason, spec.id
    sam3 = next(s for s in REQUIREMENTS if s.id == "sam3")
    assert sam3.prompt_kind == "noun-phrase" and "phrase" in sam3.data_format


def _boxes_dataset(client: TestClient, images: int, per_image: int) -> str:
    dataset_id = str(client.post("/api/v1/datasets", json={"name": "Boxes"}).json()["id"])
    box = {"label": "positive", "provenance": "hand-drawn", "prompt": "bolt", "w": 5, "h": 5}
    for i in range(images):
        boxes = [box | {"x": 1 + j, "y": 1} for j in range(per_image)]
        body = {"path": f"/b/{i}.jpg", "width": 64, "height": 64, "boxes": boxes}
        client.put(f"/api/v1/datasets/{dataset_id}/images", json=body)
    return dataset_id


def test_a_box_dataset_is_refused_for_sam_with_the_reason_and_the_fix(client: TestClient) -> None:
    dataset_id = _boxes_dataset(client, images=40, per_image=2)
    body = client.post(
        "/api/v1/finetune/check",
        json={"finetune_id": "sam2.1-hiera-small", "dataset_id": dataset_id},
    ).json()
    checks = {c["id"]: c for c in body["checks"]}
    assert body["ready"] is False
    assert checks["annotation-kind"]["passed"] is False
    assert "outline" in checks["annotation-kind"]["fix"]  # the data format, as the fix
    assert checks["recipe"]["passed"] is False and "Prepare data" in checks["recipe"]["fix"]
    assert checks["installed"]["fix"].startswith("Download it in Admin")


def test_the_same_boxes_meet_rf_detr_except_for_the_install(client: TestClient) -> None:
    dataset_id = _boxes_dataset(client, images=40, per_image=1)
    body = client.post(
        "/api/v1/finetune/check",
        json={"finetune_id": "rf-detr-nano", "dataset_id": dataset_id},
    ).json()
    checks = {c["id"]: c["passed"] for c in body["checks"]}
    assert checks == {
        "available": True,
        "installed": False,  # the test's model cache is empty
        "annotation-kind": True,
        "images": True,
        "per-class": True,
        "recipe": True,  # optional for RF-DETR
    }


def test_thin_classes_are_named(client: TestClient) -> None:
    dataset_id = _boxes_dataset(client, images=35, per_image=1)
    body = client.post(
        "/api/v1/finetune/check", json={"finetune_id": "rf-detr-nano", "dataset_id": dataset_id}
    ).json()
    per_class = next(c for c in body["checks"] if c["id"] == "per-class")
    assert per_class["passed"] is True and "bolt: 35" in per_class["detail"]
    assert client.get("/api/v1/finetune/requirements/nope").status_code == 404
    assert len(client.get("/api/v1/finetune/requirements").json()) == len(REQUIREMENTS)
