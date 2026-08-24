"""Tests for the training API and the SSE stream.

The stream is exercised against a fake runner rather than a real training run: what is
being tested is the framing and termination contract, not whether a head converges —
that is verified end-to-end against real weights outside the unit suite.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.main import create_app
from app.ml.training.config import TrainingConfig
from app.ml.training.job import EpochRecord, TrainingJob


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_connection()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_connection()
    get_settings.cache_clear()


def payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "head_type_id": "linear-classifier",
        "backbone_id": "dinov2-small",
        "dataset_ids": ["ds1"],
        "epochs": 3,
    }
    base.update(overrides)
    return base


class FakeRunner:
    """Stands in for LocalJobRunner so the API contract can be tested without torch."""

    def __init__(self) -> None:
        self.job = TrainingJob(
            job_id="job-1",
            config=TrainingConfig(
                head_type_id="linear-classifier",
                backbone_id="dinov2-small",
                dataset_ids=("ds1",),
                epochs=3,
            ),
            total_epochs=3,
            class_names=("a cat", "a dog"),
        )

    def submit(self, config: TrainingConfig) -> TrainingJob:
        return self.job

    def get(self, job_id: str) -> TrainingJob | None:
        return self.job if job_id == self.job.job_id else None

    def cancel(self, job_id: str) -> bool:
        if self.job.finished:
            return False
        self.job.cancel_requested.set()
        return True

    def list_all(self) -> list[TrainingJob]:
        return [self.job]


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeRunner:
    runner = FakeRunner()
    import app.api.v1.training as training_api

    monkeypatch.setattr(training_api, "get_job_runner", lambda: runner)
    return runner


class TestStartTraining:
    def test_rejects_an_unknown_head_type(self, client: TestClient) -> None:
        response = client.post("/api/v1/training/jobs", json=payload(head_type_id="nope"))
        assert response.status_code == 404

    def test_depth_is_409_not_400(self, client: TestClient) -> None:
        """The request is well-formed; the world makes it impossible."""
        response = client.post("/api/v1/training/jobs", json=payload(head_type_id="linear-depth"))
        assert response.status_code == 409
        assert "pretrained default" in response.json()["error"]["message"]

    def test_requires_at_least_one_dataset(self, client: TestClient) -> None:
        response = client.post("/api/v1/training/jobs", json=payload(dataset_ids=[]))
        assert response.status_code == 422

    def test_rejects_zero_epochs(self, client: TestClient) -> None:
        assert client.post("/api/v1/training/jobs", json=payload(epochs=0)).status_code == 422

    def test_rejects_splits_leaving_no_training_data(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/training/jobs", json=payload(val_fraction=0.8, test_fraction=0.3)
        )
        assert response.status_code == 422

    def test_accepts_a_valid_request(self, client: TestClient, fake: FakeRunner) -> None:
        response = client.post("/api/v1/training/jobs", json=payload())
        assert response.status_code == 202
        assert response.json()["job_id"] == "job-1"


class TestJobEndpoints:
    def test_unknown_job_is_404(self, client: TestClient, fake: FakeRunner) -> None:
        assert client.get("/api/v1/training/jobs/nope").status_code == 404

    def test_returns_declared_primary_metric(self, client: TestClient, fake: FakeRunner) -> None:
        """The UI needs to know which series is the selection criterion."""
        body = client.get("/api/v1/training/jobs/job-1").json()
        assert body["primary_metric"] == "accuracy"

    def test_history_is_exposed(self, client: TestClient, fake: FakeRunner) -> None:
        fake.job.record(
            EpochRecord(epoch=1, train_loss=0.5, val_loss=0.4, metrics={"accuracy": 0.8})
        )
        body = client.get("/api/v1/training/jobs/job-1").json()
        assert body["history"][0]["metrics"]["accuracy"] == pytest.approx(0.8)

    def test_metric_keys_are_not_constrained_by_the_schema(
        self, client: TestClient, fake: FakeRunner
    ) -> None:
        """A head type declaring miou must survive the response model untouched."""
        fake.job.record(
            EpochRecord(epoch=1, train_loss=0.5, val_loss=0.4, metrics={"miou": 0.3, "x": 1.0})
        )
        metrics = client.get("/api/v1/training/jobs/job-1").json()["history"][0]["metrics"]
        assert metrics == {"miou": 0.3, "x": 1.0}

    def test_lists_jobs(self, client: TestClient, fake: FakeRunner) -> None:
        assert len(client.get("/api/v1/training/jobs").json()["jobs"]) == 1

    def test_cancel_reports_true_while_running(self, client: TestClient, fake: FakeRunner) -> None:
        fake.job.state = "running"
        assert client.post("/api/v1/training/jobs/job-1/cancel").json()["cancelled"] is True

    def test_cancel_reports_false_when_finished(
        self, client: TestClient, fake: FakeRunner
    ) -> None:
        fake.job.finish("complete")
        assert client.post("/api/v1/training/jobs/job-1/cancel").json()["cancelled"] is False

    def test_cancel_unknown_job_is_404(self, client: TestClient, fake: FakeRunner) -> None:
        assert client.post("/api/v1/training/jobs/nope/cancel").status_code == 404


def parse_events(text: str) -> list[tuple[str, str]]:
    """Split an SSE body into (event, data) pairs, ignoring comment heartbeats."""
    events: list[tuple[str, str]] = []
    for block in text.split("\n\n"):
        name = data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        if name and data:
            events.append((name, data))
    return events


class TestEventStream:
    def test_unknown_job_is_404(self, client: TestClient, fake: FakeRunner) -> None:
        assert client.get("/api/v1/training/jobs/nope/events").status_code == 404

    def test_finished_job_streams_a_snapshot_then_terminates(
        self, client: TestClient, fake: FakeRunner
    ) -> None:
        """The generator must return on a terminal state, never hold the connection."""
        fake.job.record(
            EpochRecord(epoch=1, train_loss=0.5, val_loss=0.4, metrics={"accuracy": 0.9})
        )
        fake.job.finish("complete", "done")

        response = client.get("/api/v1/training/jobs/job-1/events")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = parse_events(response.text)
        assert [name for name, _ in events][0] == "status"
        assert events[-1][0] == "done"

    def test_epochs_recorded_during_the_stream_are_emitted(
        self, client: TestClient, fake: FakeRunner
    ) -> None:
        """The point of the feature: epochs appear as they finish, not at the end."""
        fake.job.state = "running"

        def produce() -> None:
            for epoch in range(1, 4):
                fake.job.record(
                    EpochRecord(
                        epoch=epoch,
                        train_loss=1.0 / epoch,
                        val_loss=1.0 / epoch,
                        metrics={"accuracy": 0.5 + epoch * 0.1},
                    )
                )
            fake.job.finish("complete", "done")

        threading.Timer(0.3, produce).start()
        response = client.get("/api/v1/training/jobs/job-1/events")

        events = parse_events(response.text)
        epochs = [data for name, data in events if name == "epoch"]
        assert len(epochs) == 3
        assert '"accuracy": 0.6' in epochs[0]
        assert events[-1][0] == "done"

    def test_no_buffering_header_is_set(self, client: TestClient, fake: FakeRunner) -> None:
        """A buffering proxy would hold every frame until the run ends."""
        fake.job.finish("complete")
        response = client.get("/api/v1/training/jobs/job-1/events")
        assert response.headers["x-accel-buffering"] == "no"
        assert response.headers["cache-control"] == "no-cache"

    def test_done_frame_carries_the_saved_head_id(
        self, client: TestClient, fake: FakeRunner
    ) -> None:
        """So the UI can link straight to the head without a second lookup."""
        fake.job.head_instance_id = "head-abc"
        fake.job.finish("complete")
        events = parse_events(client.get("/api/v1/training/jobs/job-1/events").text)
        assert "head-abc" in events[-1][1]
