"""A dataset as sequences to play back (docs 74, 75), through the real ASGI app.

The property that matters: a sequence is the **whole** source in order, with the frames the
Generator never saved (nothing found) merged back from disk. Otherwise playback would cut
every empty stretch out of the video, and the timeline would claim the video was shorter.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.main import create_app
from app.ml.video.extract import reset_extractor


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_extractor()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_extractor()
    get_settings.cache_clear()


@pytest.fixture
def clip(tmp_path: Path) -> Path:
    import av

    path = tmp_path / "ride.mp4"
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=10)
        stream.width, stream.height = 32, 24
        stream.pix_fmt = "yuv420p"
        for index in range(4):
            image = Image.new("RGB", (32, 24), (index * 40, 10, 10))
            container.mux(stream.encode(av.VideoFrame.from_image(image)))
        container.mux(stream.encode(None))
    return path


def _dataset(client: TestClient) -> str:
    return str(client.post("/api/v1/datasets", json={"name": "Ride"}).json()["id"])


def _box(label: str, prompt: str) -> dict[str, object]:
    return {
        "label": label,
        "provenance": "hand-drawn",
        "prompt": prompt,
        "x": 1,
        "y": 1,
        "w": 4,
        "h": 4,
    }


def _save(
    client: TestClient,
    dataset_id: str,
    path: str,
    boxes: list[dict[str, object]],
    frame: dict[str, object] | None,
) -> None:
    body: dict[str, object] = {"path": path, "width": 32, "height": 24, "boxes": boxes}
    if frame:
        body["frame"] = frame
    assert client.put(f"/api/v1/datasets/{dataset_id}/images", json=body).status_code == 200


def _extract_all(client: TestClient, dataset_id: str, clip: Path) -> list[dict[str, object]]:
    job = client.post(
        "/api/v1/video/extract",
        json={"source": str(clip), "dataset_id": dataset_id, "count": 4},
    ).json()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        body = client.get(f"/api/v1/video/extract/{job['job_id']}").json()
        if body["state"] == "complete":
            return list(body["frames"])
        time.sleep(0.05)
    raise AssertionError("extraction did not finish")


def test_a_video_plays_whole_with_the_empty_frames_merged_back(
    client: TestClient, clip: Path
) -> None:
    dataset_id = _dataset(client)
    frames = _extract_all(client, dataset_id, clip)
    # Frames 1 and 3 were annotated; 0 and 2 had nothing and were never saved.
    for index in (1, 3):
        _save(
            client,
            dataset_id,
            str(frames[index]["path"]),
            [_box("positive", "signal"), _box("negative", "noise")],
            {"sequence": str(clip), "frame_index": index},
        )

    body = client.get(f"/api/v1/datasets/{dataset_id}/sequences").json()
    [sequence] = body["sequences"]
    assert sequence["source"] == str(clip)
    assert sequence["kind"] == "video"
    assert [f["index"] for f in sequence["frames"]] == [0, 1, 2, 3]
    assert [f["annotated"] for f in sequence["frames"]] == [False, True, False, True]
    # Positive classes only: a rejected box is not "where the class can be found".
    assert [f["classes"] for f in sequence["frames"]] == [[], ["signal"], [], ["signal"]]
    assert body["class_names"] == ["signal"]
    assert body["loose"] == []


def test_a_folder_plays_in_the_order_the_generator_numbered_it(
    client: TestClient, tmp_path: Path
) -> None:
    folder = tmp_path / "shots"
    folder.mkdir()
    for name in ("a.png", "b.png", "c.png"):
        Image.new("RGB", (32, 24)).save(folder / name)
    dataset_id = _dataset(client)
    _save(
        client,
        dataset_id,
        str(folder / "c.png"),
        [_box("positive", "train")],
        {"sequence": str(folder), "frame_index": 2},
    )

    [sequence] = client.get(f"/api/v1/datasets/{dataset_id}/sequences").json()["sequences"]
    assert sequence["kind"] == "folder"
    assert [Path(f["path"]).name for f in sequence["frames"]] == ["a.png", "b.png", "c.png"]
    assert [f["classes"] for f in sequence["frames"]] == [[], [], ["train"]]


def test_a_moved_folder_still_plays_its_annotated_frames(
    client: TestClient, tmp_path: Path
) -> None:
    dataset_id = _dataset(client)
    photo = tmp_path / "x.png"
    Image.new("RGB", (32, 24)).save(photo)
    _save(
        client,
        dataset_id,
        str(photo),
        [_box("positive", "train")],
        {"sequence": str(tmp_path / "gone"), "frame_index": 7},
    )
    [sequence] = client.get(f"/api/v1/datasets/{dataset_id}/sequences").json()["sequences"]
    assert [f["index"] for f in sequence["frames"]] == [7]


def test_photos_are_loose_images(client: TestClient, tmp_path: Path) -> None:
    dataset_id = _dataset(client)
    photo = tmp_path / "cat.png"
    Image.new("RGB", (32, 24)).save(photo)
    _save(client, dataset_id, str(photo), [_box("positive", "cat")], None)

    body = client.get(f"/api/v1/datasets/{dataset_id}/sequences").json()
    assert body["sequences"] == []
    assert [f["classes"] for f in body["loose"]] == [["cat"]]
    assert body["class_names"] == ["cat"]


def test_an_unknown_dataset_is_a_404(client: TestClient) -> None:
    assert client.get("/api/v1/datasets/nope/sequences").status_code == 404
