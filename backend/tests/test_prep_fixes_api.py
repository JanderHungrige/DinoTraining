"""Safe fixes: exclusions that can be undone, class maps that never touch the data (doc 83)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.datasets.db import transaction
from app.main import create_app
from app.prep.jobs import reset_prep_runner


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_prep_runner()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_prep_runner()
    get_settings.cache_clear()


def _box(cls: str) -> dict[str, object]:
    return {
        "label": "positive",
        "provenance": "hand-drawn",
        "prompt": cls,
        "x": 10,
        "y": 10,
        "w": 60,
        "h": 40,
    }


def _dataset(client: TestClient, tmp_path: Path, spec: list[tuple[str, int, str]]) -> str:
    """spec: (file name, colour seed, class). Same seed and class = a copy."""
    dataset_id = str(client.post("/api/v1/datasets", json={"name": "Fix me"}).json()["id"])
    for name, seed, cls in spec:
        path = tmp_path / name
        rng = __import__("numpy").random.default_rng(seed)
        Image.fromarray(rng.integers(0, 255, (24, 32, 3), dtype="uint8")).resize((320, 240)).save(
            path
        )
        body = {"path": str(path), "width": 320, "height": 240, "boxes": [_box(cls)]}
        client.put(f"/api/v1/datasets/{dataset_id}/images", json=body)
    return dataset_id


def _audit(client: TestClient, dataset_id: str) -> dict[str, object]:
    job = client.post(f"/api/v1/datasets/{dataset_id}/audit", json={}).json()["job_id"]
    for _ in range(300):
        body = client.get(f"/api/v1/prep/audits/{job}").json()
        if body["state"] == "complete":
            return body["audit"]  # type: ignore[no-any-return]
        time.sleep(0.02)
    raise AssertionError("audit did not finish")


def _fix(client: TestClient, dataset_id: str, **body: object) -> dict[str, object]:
    response = client.post(f"/api/v1/datasets/{dataset_id}/fixes", json=body)
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore[no-any-return]


def test_excluding_is_reversible_and_the_audit_follows(client: TestClient, tmp_path: Path) -> None:
    dataset_id = _dataset(client, tmp_path, [("a.png", 1, "car"), ("b.png", 2, "car")])
    target = str(tmp_path / "a.png")
    assert _fix(client, dataset_id, action="exclude", paths=[target])["changed"] == 1
    audit = _audit(client, dataset_id)
    assert audit["summary"]["images"] == 1  # type: ignore[index]
    assert audit["excluded"] == 1

    result = _fix(client, dataset_id, action="include", paths=[target])
    assert result["changed"] == 1
    assert result["state"]["excluded"] == []  # type: ignore[index]
    assert _audit(client, dataset_id)["summary"]["images"] == 2  # type: ignore[index]


def test_copies_are_reduced_to_one_and_scene_twins_are_kept(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id = _dataset(
        client,
        tmp_path,
        [("a.png", 1, "car"), ("b.png", 1, "car"), ("c.png", 1, "car"), ("d.png", 1, "bus")],
    )
    assert _audit(client, dataset_id)["copy_groups"]  # a, b, c: same picture, same box
    result = _fix(client, dataset_id, action="exclude-copies")
    assert result["changed"] == 2
    # d shows the same picture with a different class: a different example, kept.
    assert str(tmp_path / "d.png") not in result["state"]["excluded"]  # type: ignore[operator]


def test_a_class_map_merges_and_drops_without_touching_the_data(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id = _dataset(
        client,
        tmp_path,
        [("a.png", 1, "Traffic Lights"), ("b.png", 2, "traffic-light"), ("c.png", 3, "bishop")],
    )
    _fix(
        client,
        dataset_id,
        action="set-class-map",
        class_map={"traffic lights": "traffic-light", "bishop": None},
    )
    classes = _audit(client, dataset_id)["summary"]["classes"]  # type: ignore[index]
    assert classes == {"traffic-light": 2}
    with transaction() as connection:
        stored = {row[0] for row in connection.execute("SELECT prompt FROM boxes")}
    assert stored == {"Traffic Lights", "traffic-light", "bishop"}


def test_fixes_that_need_findings_ask_for_an_audit_first(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id = _dataset(client, tmp_path, [("a.png", 1, "car")])
    response = client.post(
        f"/api/v1/datasets/{dataset_id}/fixes", json={"action": "exclude-copies"}
    )
    assert response.status_code == 409


def test_an_unknown_path_is_refused_by_name(client: TestClient, tmp_path: Path) -> None:
    dataset_id = _dataset(client, tmp_path, [("a.png", 1, "car")])
    response = client.post(
        f"/api/v1/datasets/{dataset_id}/fixes", json={"action": "exclude", "paths": ["/nope.png"]}
    )
    assert response.status_code == 422
    assert "/nope.png" in response.json()["error"]["message"] or "/nope.png" in response.text
