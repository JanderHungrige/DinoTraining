"""The dataset audit through the real ASGI app (doc 81)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.main import create_app
from app.prep.jobs import reset_prep_runner


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_prep_runner()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_prep_runner()
    get_settings.cache_clear()


def _dataset(client: TestClient, tmp_path: Path, images: int) -> str:
    dataset_id = str(client.post("/api/v1/datasets", json={"name": "Audit me"}).json()["id"])
    for index in range(images):
        path = tmp_path / f"img{index}.png"
        Image.new("RGB", (640, 480), (index * 30 % 255, 90, 160)).save(path)
        box = {
            "label": "positive",
            "provenance": "hand-drawn",
            "prompt": "car",
            "x": 10,
            "y": 10,
            "w": 200,
            "h": 150,
        }
        body = {"path": str(path), "width": 640, "height": 480, "boxes": [box]}
        assert client.put(f"/api/v1/datasets/{dataset_id}/images", json=body).status_code == 200
    return dataset_id


def _finish(client: TestClient, job_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        body: dict[str, object] = client.get(f"/api/v1/prep/audits/{job_id}").json()
        if body["state"] in {"complete", "failed"}:
            return body
        time.sleep(0.05)
    raise AssertionError("audit did not finish")


def test_an_audit_reports_findings_and_is_kept(client: TestClient, tmp_path: Path) -> None:
    dataset_id = _dataset(client, tmp_path, 5)
    started = client.post(f"/api/v1/datasets/{dataset_id}/audit", json={"target": "rf-detr-nano"})
    assert started.status_code == 202
    body = _finish(client, started.json()["job_id"])

    assert body["state"] == "complete"
    audit = body["audit"]
    assert isinstance(audit, dict)
    assert audit["summary"]["images"] == 5
    assert audit["summary"]["classes"] == {"car": 5}
    found = {f["id"]: f for f in audit["findings"]}
    assert found["small-dataset"]["severity"] == "problem"
    assert found["small-dataset"]["why"]  # every finding explains itself

    kept = client.get(f"/api/v1/datasets/{dataset_id}/audit")
    assert kept.status_code == 200
    assert kept.json()["facts_hash"] == audit["facts_hash"]


def test_a_missing_file_is_a_finding_not_a_failure(client: TestClient, tmp_path: Path) -> None:
    dataset_id = _dataset(client, tmp_path, 3)
    (tmp_path / "img1.png").unlink()
    job = client.post(f"/api/v1/datasets/{dataset_id}/audit", json={}).json()
    body = _finish(client, job["job_id"])
    assert body["state"] == "complete"
    found = {f["id"]: f for f in body["audit"]["findings"]}  # type: ignore[index]
    assert found["unreadable-images"]["examples"] == [str(tmp_path / "img1.png")]


def test_targets_are_listed_with_what_they_need(client: TestClient) -> None:
    targets = {t["id"]: t for t in client.get("/api/v1/prep/targets").json()}
    assert targets["rf-detr-nano"]["input_size"] == 384
    assert targets["head-segmentation-dinov2"]["annotation_kind"] == "masks"


@pytest.mark.parametrize(
    ("path", "body", "status"),
    [
        ("/api/v1/datasets/nope/audit", {}, 404),
        ("/api/v1/datasets/{id}/audit", {"target": "no-such-model"}, 422),
    ],
)
def test_bad_requests(
    client: TestClient, tmp_path: Path, path: str, body: dict[str, str], status: int
) -> None:
    dataset_id = _dataset(client, tmp_path, 1)
    assert client.post(path.replace("{id}", dataset_id), json=body).status_code == status


def test_an_unaudited_dataset_has_no_report(client: TestClient, tmp_path: Path) -> None:
    dataset_id = _dataset(client, tmp_path, 1)
    assert client.get(f"/api/v1/datasets/{dataset_id}/audit").status_code == 404
