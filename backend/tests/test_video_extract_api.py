"""A video as a Dataset Generator source, through the real ASGI app (doc 73).

Two halves: decoding a range into the dataset, and the dataset remembering where each saved
frame sits in its video, which is what lets doc 74 play it back in order.
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

FRAME_COUNT = 8


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

    path = tmp_path / "track.mp4"
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=10)
        stream.width, stream.height = 32, 24
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "0", "preset": "ultrafast"}
        for index in range(FRAME_COUNT):
            image = Image.new("RGB", (32, 24), (index * 20, 10, 10))
            container.mux(stream.encode(av.VideoFrame.from_image(image)))
        container.mux(stream.encode(None))
    return path


def _dataset(client: TestClient, copy_images: bool = False) -> str:
    response = client.post(
        "/api/v1/datasets", json={"name": "Track", "copy_images": copy_images}
    )
    assert response.status_code in (200, 201), response.text
    return str(response.json()["id"])


def _extract(client: TestClient, dataset_id: str, clip: Path, **range_: int) -> dict[str, object]:
    started = client.post(
        "/api/v1/video/extract",
        json={"source": str(clip), "dataset_id": dataset_id, **range_},
    )
    assert started.status_code == 202, started.text
    job_id = started.json()["job_id"]
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        body: dict[str, object] = client.get(f"/api/v1/video/extract/{job_id}").json()
        if body["state"] in {"complete", "failed", "cancelled"}:
            return body
        time.sleep(0.05)
    raise AssertionError("extraction did not finish")


class TestExtract:
    def test_frames_are_decoded_into_the_dataset(self, client: TestClient, clip: Path) -> None:
        dataset_id = _dataset(client)
        body = _extract(client, dataset_id, clip, start=1, count=3, stride=2)

        assert body["state"] == "complete"
        frames = body["frames"]
        assert isinstance(frames, list)
        assert [frame["index"] for frame in frames] == [1, 3, 5]
        data_dir = get_settings().data_dir
        for frame in frames:
            path = Path(frame["path"])
            assert path.is_file()
            # Inside this dataset's directory, so the frames go wherever the dataset goes.
            assert path.is_relative_to(Path(data_dir) / "datasets" / dataset_id)

    def test_the_total_is_what_the_video_can_give(self, client: TestClient, clip: Path) -> None:
        body = _extract(client, _dataset(client), clip, start=6, count=100)
        assert body["total"] == 2
        assert body["done"] == 2

    @pytest.mark.parametrize(
        ("change", "status"),
        [
            ({"dataset_id": "no-such-dataset"}, 404),
            ({"source": "/nowhere/gone.mp4"}, 404),
            ({"source": "/nowhere/photo.png"}, 422),
            ({"start": 50}, 422),
            ({"count": 0}, 422),
        ],
    )
    def test_bad_requests_say_what_is_wrong(
        self, client: TestClient, clip: Path, change: dict[str, object], status: int
    ) -> None:
        payload = {"source": str(clip), "dataset_id": _dataset(client), **change}
        response = client.post("/api/v1/video/extract", json=payload)
        assert response.status_code == status, response.text

    def test_a_file_that_is_not_a_video_is_a_415(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        fake = tmp_path / "fake.mp4"
        fake.write_text("not a video")
        response = client.post(
            "/api/v1/video/extract", json={"source": str(fake), "dataset_id": _dataset(client)}
        )
        assert response.status_code == 415

    def test_an_unknown_job_is_a_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/video/extract/nope").status_code == 404


class TestFramePositions:
    def _save(
        self, client: TestClient, dataset_id: str, path: str, frame: dict[str, object] | None
    ) -> None:
        body: dict[str, object] = {"path": path, "width": 32, "height": 24, "boxes": []}
        if frame is not None:
            body["frame"] = frame
        response = client.put(f"/api/v1/datasets/{dataset_id}/images", json=body)
        assert response.status_code == 200, response.text

    def _listing(self, client: TestClient, dataset_id: str) -> dict[str, dict[str, object]]:
        images = client.get(f"/api/v1/datasets/{dataset_id}/images").json()["images"]
        return {image["path"]: image for image in images}

    def test_a_saved_frame_remembers_its_video_and_number(
        self, client: TestClient, clip: Path
    ) -> None:
        dataset_id = _dataset(client)
        frames = _extract(client, dataset_id, clip, count=2)["frames"]
        assert isinstance(frames, list)
        path = frames[1]["path"]
        self._save(client, dataset_id, path, {"sequence": str(clip), "frame_index": 1})

        listed = self._listing(client, dataset_id)[path]
        assert listed["sequence"] == str(clip)
        assert listed["frame_index"] == 1

    def test_saving_again_without_a_position_keeps_it(
        self, client: TestClient, clip: Path
    ) -> None:
        # Re-reviewing through the dataset-as-source path knows nothing of the video.
        dataset_id = _dataset(client)
        frames = _extract(client, dataset_id, clip, count=1)["frames"]
        assert isinstance(frames, list)
        path = frames[0]["path"]
        self._save(client, dataset_id, path, {"sequence": str(clip), "frame_index": 0})
        self._save(client, dataset_id, path, None)

        assert self._listing(client, dataset_id)[path]["sequence"] == str(clip)

    def test_a_photo_has_no_position(self, client: TestClient, tmp_path: Path) -> None:
        dataset_id = _dataset(client)
        photo = tmp_path / "cat.png"
        Image.new("RGB", (32, 24)).save(photo)
        self._save(client, dataset_id, str(photo), None)
        listed = self._listing(client, dataset_id)[str(photo)]
        assert listed["sequence"] is None
        assert listed["frame_index"] is None

    def test_a_copying_dataset_does_not_store_its_own_frames_twice(
        self, client: TestClient, clip: Path
    ) -> None:
        dataset_id = _dataset(client, copy_images=True)
        frames = _extract(client, dataset_id, clip, count=1)["frames"]
        assert isinstance(frames, list)
        path = frames[0]["path"]
        self._save(client, dataset_id, path, {"sequence": str(clip), "frame_index": 0})

        assert list(self._listing(client, dataset_id)) == [path]
        images_dir = Path(get_settings().data_dir) / "datasets" / dataset_id / "images"
        assert not images_dir.exists() or not any(images_dir.iterdir())
