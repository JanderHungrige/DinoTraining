"""The outline-editing routes (doc 106), with SAM 2 replaced by a stand-in."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.v1 import segment as route
from app.datasets.rle import rle_encode
from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def picture(tmp_path: Path) -> str:
    path = tmp_path / "p.png"
    Image.new("RGB", (40, 30), "white").save(path)
    return str(path)


@pytest.fixture
def fake_sam(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    calls: list[Any] = []
    monkeypatch.setattr(route, "load_segmenter", lambda model_id: object())

    def refined(_s: object, image: Image.Image, box: Any, points: Any) -> tuple[np.ndarray, float]:
        calls.append((box, points))
        mask = np.zeros((image.height, image.width), dtype=bool)
        mask[5:10, 5 + len(points) : 15] = True
        return mask, 0.9

    def boxes(_s: object, image: Image.Image, prompts: Any) -> tuple[np.ndarray, list[float]]:
        calls.append(prompts)
        masks = np.zeros((len(prompts), image.height, image.width), dtype=bool)
        for i, (x0, y0, x1, y1) in enumerate(prompts):
            masks[i, int(y0) : int(y1), int(x0) : int(x1)] = True
        return masks, [0.8] * len(prompts)

    monkeypatch.setattr(route, "segment_refined", refined)
    monkeypatch.setattr(route, "segment_boxes", boxes)
    return calls


def test_refine_sends_box_and_clicks_and_returns_the_outline(
    client: TestClient, picture: str, fake_sam: list[Any]
) -> None:
    body = {
        "image_path": picture,
        "box": {"x": 2, "y": 3, "w": 20, "h": 10},
        "points": [{"x": 8, "y": 7, "positive": True}, {"x": 12, "y": 7, "positive": False}],
    }
    result = client.post("/api/v1/segment/refine", json=body).json()
    assert fake_sam == [((2, 3, 22, 13), [(8, 7, True), (12, 7, False)])]
    assert (result["x"], result["y"], result["w"], result["h"]) == (7, 5, 8, 5)
    assert result["rle"]["size"] == [30, 40] and result["mask_png"] and result["score"] == 0.9


def test_outlines_from_boxes_keep_the_order(
    client: TestClient, picture: str, fake_sam: list[Any]
) -> None:
    body = {
        "image_path": picture,
        "boxes": [{"x": 1, "y": 1, "w": 5, "h": 5}, {"x": 20, "y": 10, "w": 8, "h": 4}],
    }
    masks = client.post("/api/v1/segment/boxes", json=body).json()["masks"]
    assert [(m["x"], m["w"]) for m in masks] == [(1, 5), (20, 8)]


def test_refusals(client: TestClient, picture: str, fake_sam: list[Any]) -> None:
    outside = {"image_path": picture, "box": {"x": 50, "y": 1, "w": 5, "h": 5}}
    assert client.post("/api/v1/segment/refine", json=outside).status_code == 422
    missing = {"image_path": "/nope.png", "box": {"x": 1, "y": 1, "w": 5, "h": 5}}
    assert client.post("/api/v1/segment/refine", json=missing).status_code == 404


def test_the_stroke_paints_and_an_empty_result_is_refused(client: TestClient) -> None:
    mask = np.zeros((20, 20), dtype=bool)
    mask[5:10, 5:10] = True
    counts, size = rle_encode(mask)
    rle = {"size": list(size), "counts": counts}
    painted = client.post(
        "/api/v1/segment/stroke", json={"rle": rle, "points": [[15, 15]], "radius": 2}
    ).json()
    assert painted["w"] > 5
    wiped = client.post(
        "/api/v1/segment/stroke",
        json={"rle": rle, "points": [[7.5, 7.5]], "radius": 10, "erase": True},
    )
    assert wiped.status_code == 422
    assert "reject it instead" in wiped.json()["error"]["message"]
