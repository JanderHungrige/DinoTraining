"""The playback endpoints, through the real ASGI app (doc 68).

The models are stubbed — a real Grounded SAM pass is 5 s a frame and what is being tested
here is the *job*, not the inference. What is deliberately **not** stubbed is the decoding:
a real mp4 is written, because "frame N back is frame N" has to survive the route as well
as the decoder.
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
from app.ml.inference.results import Prediction
from app.ml.video.runner import reset_runner

FRAME_COUNT = 6
STEP = 20


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_runner()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_runner()
    get_settings.cache_clear()


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    directory = tmp_path / "frames"
    directory.mkdir()
    for index in range(FRAME_COUNT):
        Image.new("RGB", (32, 24), (index * STEP, 10, 10)).save(
            directory / f"f{index:02d}.png"
        )
    return directory


@pytest.fixture
def clip(tmp_path: Path) -> Path:
    import av

    path = tmp_path / "clip.mp4"
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=10)
        stream.width, stream.height = 32, 24
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "0", "preset": "ultrafast"}
        for index in range(FRAME_COUNT):
            image = Image.new("RGB", (32, 24), (index * STEP, 10, 10))
            container.mux(stream.encode(av.VideoFrame.from_image(image)))
        container.mux(stream.encode(None))
    return path


@pytest.fixture
def stub_models(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Replace inference with something instant that records which frames it saw."""
    seen: list[int] = []

    def fake_predict(model: object, image: Image.Image, *args: object, **kwargs: object):
        # The frame identifies itself in its pixels, so the run can be checked against the
        # frames it was *supposed* to cover rather than against a call count.
        seen.append(round(image.getpixel((16, 12))[0] / STEP))  # type: ignore[index]
        return Prediction(
            instance_id="stub",
            head_name="Stub",
            head_type_id="stub",
            task="detection",
            render_hint="boxes",
            class_names=("thing",),
            payload={"boxes": [[1.0, 2.0, 3.0, 4.0]], "scores": [0.9], "classes": [0]},
            elapsed_ms=1.0,
        )

    monkeypatch.setattr("app.ml.video.runner.build_foundation", lambda *a, **k: object())
    monkeypatch.setattr("app.ml.video.runner.predict_with", fake_predict)
    return seen


def wait_for(client: TestClient, job_id: str, timeout: float = 10.0) -> dict:
    """Poll until the run is finished. The worker is a real thread."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/v1/video/runs/{job_id}").json()
        if body["state"] in {"complete", "failed", "cancelled"}:
            return body
        time.sleep(0.02)
    raise AssertionError(f"Run {job_id} did not finish: {body}")


class TestProbe:
    def test_a_folder_reports_its_frames_and_no_rate(
        self, client: TestClient, folder: Path
    ) -> None:
        body = client.get("/api/v1/video/probe", params={"path": str(folder)}).json()
        assert body["kind"] == "folder"
        assert body["frames"] == FRAME_COUNT
        # Not defaulted to 30 — a made-up rate drives a playback speed nobody chose.
        assert body["fps"] is None

    def test_a_video_reports_its_rate(self, client: TestClient, clip: Path) -> None:
        body = client.get("/api/v1/video/probe", params={"path": str(clip)}).json()
        assert body["kind"] == "video"
        assert body["frames"] == FRAME_COUNT
        assert body["fps"] == pytest.approx(10)

    def test_a_missing_path_is_404(self, client: TestClient, tmp_path: Path) -> None:
        response = client.get("/api/v1/video/probe", params={"path": str(tmp_path / "no")})
        assert response.status_code == 404

    def test_an_unplayable_file_is_415(self, client: TestClient, tmp_path: Path) -> None:
        odd = tmp_path / "notes.bin"
        odd.write_bytes(b"\x00")
        response = client.get("/api/v1/video/probe", params={"path": str(odd)})
        assert response.status_code == 415


class TestFrame:
    def test_it_serves_the_frame_asked_for(self, client: TestClient, clip: Path) -> None:
        """Through the route, not just the decoder — the index has to survive the wire."""
        import io

        response = client.get(
            "/api/v1/video/frame", params={"path": str(clip), "index": 4}
        )
        assert response.status_code == 200
        image = Image.open(io.BytesIO(response.content))
        assert round(image.getpixel((16, 12))[0] / STEP) == 4  # type: ignore[index]

    def test_a_frame_past_the_end_is_404(self, client: TestClient, clip: Path) -> None:
        response = client.get(
            "/api/v1/video/frame", params={"path": str(clip), "index": FRAME_COUNT}
        )
        assert response.status_code == 404

    def test_frames_are_cacheable(self, client: TestClient, clip: Path) -> None:
        """A given (path, index) is immutable, and scrubbing backwards over a video is
        otherwise a full re-decode per frame."""
        response = client.get(
            "/api/v1/video/frame", params={"path": str(clip), "index": 1}
        )
        assert "max-age" in response.headers.get("cache-control", "")


class TestTheRun:
    def start(self, client: TestClient, source: Path, **over: object) -> dict:
        payload = {
            "source": str(source),
            "start": 0,
            "count": FRAME_COUNT,
            "foundation_ids": ["rf-detr-nano"],
            **over,
        }
        response = client.post("/api/v1/video/runs", json=payload)
        assert response.status_code == 202, response.text
        return response.json()

    def test_it_returns_a_job_immediately(
        self, client: TestClient, folder: Path, stub_models: list[int]
    ) -> None:
        # A 120-frame range is minutes. Blocking the request would hit a client timeout.
        body = self.start(client, folder)
        assert body["job_id"]
        assert body["total"] == FRAME_COUNT

    def test_it_covers_exactly_the_frames_asked_for(
        self, client: TestClient, folder: Path, stub_models: list[int]
    ) -> None:
        """Checked against which frames the model actually *saw*, read out of the pixels,
        rather than against a count — a run that did six frames starting from the wrong
        one has the right count and the wrong answer."""
        body = self.start(client, folder, start=2, count=3)
        wait_for(client, body["job_id"])

        assert stub_models == [2, 3, 4]

    def test_a_range_past_the_end_is_clamped_not_refused(
        self, client: TestClient, folder: Path, stub_models: list[int]
    ) -> None:
        # "the rest" is what someone asking for 500 frames from frame 4 means.
        body = self.start(client, folder, start=4, count=500)
        wait_for(client, body["job_id"])

        assert stub_models == [4, 5]

    def test_it_reports_predictions_per_frame(
        self, client: TestClient, folder: Path, stub_models: list[int]
    ) -> None:
        body = self.start(client, folder, count=2)
        wait_for(client, body["job_id"])

        polled = client.get(
            f"/api/v1/video/runs/{body['job_id']}", params={"since": 0, "until": 2}
        ).json()
        assert [frame["index"] for frame in polled["frames"]] == [0, 1]
        assert polled["frames"][0]["predictions"][0]["head_name"] == "Stub"

    def test_polling_returns_only_the_window_asked_for(
        self, client: TestClient, folder: Path, stub_models: list[int]
    ) -> None:
        """Without a window a poll re-sends every finished frame every second, and a
        500-frame run with masks re-sends megabytes the player already has."""
        body = self.start(client, folder)
        wait_for(client, body["job_id"])

        polled = client.get(
            f"/api/v1/video/runs/{body['job_id']}", params={"since": 3, "until": 5}
        ).json()
        assert [frame["index"] for frame in polled["frames"]] == [3, 4]

    def test_it_works_on_a_video_too(
        self, client: TestClient, clip: Path, stub_models: list[int]
    ) -> None:
        # The same run, the other source kind — the point of one FrameSequence contract.
        body = self.start(client, clip, count=3)
        wait_for(client, body["job_id"])

        assert stub_models == [0, 1, 2]

    def test_selecting_nothing_is_refused(self, client: TestClient, folder: Path) -> None:
        # An empty run would finish instantly and report success over nothing.
        response = client.post(
            "/api/v1/video/runs",
            json={"source": str(folder), "foundation_ids": [], "instance_ids": []},
        )
        assert response.status_code == 422

    def test_heads_without_a_backbone_are_refused(
        self, client: TestClient, folder: Path
    ) -> None:
        response = client.post(
            "/api/v1/video/runs",
            json={"source": str(folder), "instance_ids": ["h1"], "backbone_id": ""},
        )
        assert response.status_code == 422

    def test_a_start_past_the_end_is_refused(
        self, client: TestClient, folder: Path
    ) -> None:
        # Unlike an over-long count, there is no "rest" to give.
        response = client.post(
            "/api/v1/video/runs",
            json={
                "source": str(folder),
                "start": FRAME_COUNT + 1,
                "count": 2,
                "foundation_ids": ["rf-detr-nano"],
            },
        )
        assert response.status_code == 422

    def test_an_unknown_job_is_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/video/runs/nope").status_code == 404


class TestCancelling:
    def test_it_keeps_the_frames_it_finished(
        self, client: TestClient, folder: Path, stub_models: list[int]
    ) -> None:
        """The user asked it to stop, not to throw away the part they can already watch."""
        response = client.post(
            "/api/v1/video/runs",
            json={
                "source": str(folder),
                "count": FRAME_COUNT,
                "foundation_ids": ["rf-detr-nano"],
            },
        )
        job_id = response.json()["job_id"]
        wait_for(client, job_id)

        cancelled = client.delete(f"/api/v1/video/runs/{job_id}").json()
        # Already complete, so cancelling changes nothing and must not erase the result.
        assert cancelled["done"] == FRAME_COUNT

    def test_cancelling_an_unknown_job_is_404(self, client: TestClient) -> None:
        assert client.delete("/api/v1/video/runs/nope").status_code == 404
