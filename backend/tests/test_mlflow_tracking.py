"""MLflow tracking (doc 123): lazily begun, never at the cost of training."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.ml.training.config import TrainingConfig
from app.ml.training.job import JOB_HOOKS, EpochRecord, TrainingJob
from app.mlops import tracking, tracking_hooks
from app.mlops.mlflow_client import MlflowError
from app.mlops.tracking import MlflowTracker
from tests.datasets_api_testkit import dataset_client


class FakeClient:
    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.fail_on = fail_on

    def _hit(self, name: str, *args: Any) -> None:
        self.calls.append((name, args))
        if name == self.fail_on:
            raise MlflowError("MLflow at http://m is not reachable: refused")

    def experiment_id(self, name: str) -> str:
        self._hit("experiment_id", name)
        return "1"

    def create_run(self, experiment: str, name: str, tags: dict[str, str]) -> tuple[str, str]:
        self._hit("create_run", name, tags)
        return "r1", "mlflow-artifacts:/1/r1/artifacts"

    def log_params(self, run_id: str, params: dict[str, str]) -> None:
        self._hit("log_params", params)

    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int) -> None:
        self._hit("log_metrics", metrics, step)

    def end_run(self, run_id: str, status: str) -> None:
        self._hit("end_run", status)


def _tracker(client: FakeClient, notes: list[str]) -> MlflowTracker:
    settings = get_settings()
    return MlflowTracker(client, settings, notes.append, ("run", {"a": {"b": 1}}, {"t": "v"}))  # type: ignore[arg-type]


def test_begins_on_the_first_epoch_not_at_submit() -> None:
    client, notes = FakeClient(), []
    tracker = _tracker(client, notes)
    assert client.calls == []
    tracker.epoch(1, {"train_loss": 0.5})
    assert [name for name, _ in client.calls] == [
        "experiment_id",
        "create_run",
        "log_params",
        "log_metrics",
    ]
    assert client.calls[2][1][0] == {"a.b": "1"}  # nested settings flattened


def test_the_first_failure_is_one_note_and_tracking_stops() -> None:
    client, notes = FakeClient(fail_on="log_metrics"), []
    tracker = _tracker(client, notes)
    tracker.epoch(1, {"train_loss": 0.5})
    tracker.epoch(2, {"train_loss": 0.4})
    tracker.finished("complete")
    assert notes == ["MLflow: MLflow at http://m is not reachable: refused"]
    assert [name for name, _ in client.calls].count("log_metrics") == 1
    # The run is still ended, best effort, without a second note (see below).


@pytest.fixture
def tracked(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow.test")
    get_settings.cache_clear()
    client = FakeClient()
    monkeypatch.setattr(tracking, "MlflowClient", lambda _settings: client)
    monkeypatch.setattr(
        tracking, "log_model", lambda *args: client.calls.append(("log_model", args[4:]))
    )
    tracking_hooks.install()
    yield client
    JOB_HOOKS.remove(tracking_hooks._attach)


def _job() -> TrainingJob:
    return TrainingJob(
        job_id="j1", config=TrainingConfig("dense-detector", "dinov2-small", ("d1",))
    )


def test_a_head_run_logs_epochs_then_the_saved_model(tracked: FakeClient) -> None:
    job = _job()
    job.record(EpochRecord(epoch=1, train_loss=0.9, val_loss=1.0, metrics={"map": 0.2}))
    job.best_state = {}  # as the runner holds them before it finishes
    job.finish("complete")
    job.mark_saved("h1")
    names = [name for name, _ in tracked.calls]
    assert names == [
        "experiment_id",
        "create_run",
        "log_params",
        "log_metrics",
        "log_model",
        "end_run",
    ]
    assert tracked.calls[3][1] == ({"train_loss": 0.9, "val_loss": 1.0, "map": 0.2}, 1)
    assert tracked.calls[-2][1] == ("heads", "h1")
    assert tracked.calls[-1][1] == ("FINISHED",)


def test_a_cancelled_run_ends_killed(tracked: FakeClient) -> None:
    job = _job()
    job.record(EpochRecord(epoch=1, train_loss=0.9, val_loss=1.0, metrics={}))
    job.finish("cancelled", "stopped")
    assert tracked.calls[-1] == ("end_run", ("KILLED",))


def test_without_mlflow_nothing_is_attached() -> None:
    tracking_hooks.install()
    try:
        assert _job().listeners == []
    finally:
        JOB_HOOKS.remove(tracking_hooks._attach)


# --- settings API -----------------------------------------------------------------------


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("DINO_ENV_FILE", str(tmp_path / ".env"))
    get_settings.cache_clear()
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


async def test_settings_go_to_env_and_secrets_never_come_back(
    client: AsyncClient, tmp_path: Path
) -> None:
    body = {
        "uri": "http://127.0.0.1:1",
        "experiment": "Screws",
        "username": "jan",
        "password": "s3cret",
    }
    status = (await client.put("/api/v1/mlops/settings", json=body)).json()
    assert status == {
        "configured": True,
        "uri": "http://127.0.0.1:1",
        "experiment": "Screws",
        "register_models": True,
        "auth": "basic",
        "username": "jan",
    }
    assert "s3cret" in (tmp_path / ".env").read_text()
    assert "s3cret" not in (await client.get("/api/v1/mlops/status")).text
    tested = (await client.post("/api/v1/mlops/test")).json()
    assert tested["ok"] is False and "not reachable" in tested["message"]
    off = (await client.delete("/api/v1/mlops/settings")).json()
    assert off["configured"] is False and off["auth"] == "none"


async def test_a_uri_without_a_scheme_is_refused(client: AsyncClient) -> None:
    response = await client.put("/api/v1/mlops/settings", json={"uri": "localhost:5000"})
    assert response.status_code == 422


def test_a_registry_name_has_no_colon_or_slash() -> None:
    """Found live: MLflow refused 'Object detection: black-bishop +11 more'."""
    from app.mlops.tracking import registry_name

    assert (
        registry_name("Object detection: black-bishop +11 more")
        == "Object detection - black-bishop +11 more"
    )
    assert registry_name("a/b:c") == "a - b - c"
    assert registry_name(":") == "model"


def test_the_run_is_ended_even_after_tracking_stopped() -> None:
    """Found live: a failed registration left the run RUNNING."""
    client, notes = FakeClient(fail_on="log_metrics"), []
    tracker = _tracker(client, notes)
    tracker.epoch(1, {"train_loss": 0.5})
    tracker.finished("complete")
    assert ("end_run", ("FINISHED",)) in client.calls
    assert len(notes) == 1
