"""The shared fine-tune runner, with a fake adapter (doc 93)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.finetune import runner as runner_module
from app.finetune.adapter import FinetuneData, FinetuneSettings
from app.finetune.preflight import Readiness
from app.finetune.runner import FinetuneRequest, FoundationFinetuneRunner
from app.main import create_app
from app.ml.foundation.instances import FoundationInstanceStore
from app.ml.training.samples import TrainingSample

#: Validation scores by epoch; epoch 2 is the best and must be the one saved.
SCORES = [0.2, 0.5, 0.4]


class FakeAdapter:
    finetune_id = "fake"
    primary_metric = "miou"
    weights_kind = "sam-mask-decoder"

    def prepare(self, data, settings, app_settings):  # type: ignore[no-untyped-def]
        return {"epoch": 0}

    def train_epoch(self, state, data, epoch):  # type: ignore[no-untyped-def]
        state["epoch"] = epoch
        return 1.0 / epoch

    base = 0.1

    def evaluate(self, state, samples):  # type: ignore[no-untyped-def]
        return {"miou": self.base if state["epoch"] == 0 else SCORES[state["epoch"] - 1]}

    def snapshot(self, state):  # type: ignore[no-untyped-def]
        return state["epoch"]

    def restore(self, state, snapshot):  # type: ignore[no-untyped-def]
        state["epoch"] = snapshot

    def save(self, state, directory: Path) -> None:  # type: ignore[no-untyped-def]
        (directory / "decoder.pt").write_text(f"epoch {state['epoch']}")


def sample(split: str) -> TrainingSample:
    return TrainingSample(f"/{split}.jpg", 8, 8, split=split, segmented=True)


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_connection()
    monkeypatch.setattr(runner_module, "get_adapter", lambda _id: FakeAdapter())
    monkeypatch.setattr(
        runner_module,
        "preflight",
        lambda *a, **k: Readiness(
            finetune_id="sam2.1-hiera-small", dataset_id="d", recipe_id=None, ready=True, checks=[]
        ),
    )
    yield
    reset_connection()
    get_settings.cache_clear()


def run(monkeypatch: pytest.MonkeyPatch, data: FinetuneData):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner_module, "load_data", lambda *a, **k: data)
    runner = FoundationFinetuneRunner()
    job = runner.submit(
        FinetuneRequest("sam2.1-hiera-small", ("d",), "mine", "r1", FinetuneSettings(epochs=3))
    )
    deadline = time.monotonic() + 10
    while not job.finished and time.monotonic() < deadline:
        time.sleep(0.02)
    return job


def test_the_best_epoch_is_scored_against_the_base_on_the_same_pictures_and_saved(
    env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = run(
        monkeypatch, FinetuneData([sample("train")], [sample("val")], [sample("test")], ("cell",))
    )
    assert job.state == "complete", job.message
    assert job.baseline_metrics == {"miou": 0.1}
    assert job.final_metrics == {"miou": 0.5}  # epoch 2 restored, not the last epoch
    assert job.held_out == "test" and job.notes == []
    saved = FoundationInstanceStore().get(job.instance_id or "")
    assert saved is not None
    assert (saved.baseline_metrics, saved.metrics, saved.recipe_id) == (
        {"miou": 0.1},
        {"miou": 0.5},
        "r1",
    )
    assert saved.weights_kind == "sam-mask-decoder" and saved.finetune_id == "sam2.1-hiera-small"
    assert (FoundationInstanceStore().directory(saved.id) / "decoder.pt").read_text() == "epoch 2"


def test_when_no_epoch_beats_the_base_nothing_is_saved_and_the_job_says_so(
    env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Found live (doc 94): SAM 2 on easy shapes scored 0.957 before and 0.936 after, and
    # the first runner saved the worse model as the "fine-tuned" one.
    monkeypatch.setattr(FakeAdapter, "base", 0.9)
    job = run(
        monkeypatch, FinetuneData([sample("train")], [sample("val")], [sample("test")], ("cell",))
    )
    assert job.state == "complete" and job.best_epoch == 0
    assert job.instance_id is None and FoundationInstanceStore().list_all() == []
    assert job.final_metrics == job.baseline_metrics == {"miou": 0.9}
    assert "No epoch beat the base model" in job.notes[0] and "0.900" in job.notes[0]


def test_without_a_test_side_the_comparison_says_it_is_optimistic(
    env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = run(monkeypatch, FinetuneData([sample("train")], [sample("val")], [], ("cell",)))
    assert job.held_out == "validation"
    assert "optimistic" in job.notes[0]


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


def test_a_dataset_that_breaks_the_rules_is_refused_before_any_work(client: TestClient) -> None:
    dataset_id = client.post("/api/v1/datasets", json={"name": "Empty"}).json()["id"]
    response = client.post(
        "/api/v1/finetune/jobs",
        json={"finetune_id": "rf-detr-nano", "dataset_ids": [dataset_id], "name": "x"},
    )
    assert response.status_code == 409
    message = str(response.json())
    assert "installed" in message and "boxes" in message  # the failed rules, named
    assert client.get("/api/v1/finetune/jobs").json() == []  # nothing was started
    unknown = client.post(
        "/api/v1/finetune/jobs",
        json={"finetune_id": "nope", "dataset_ids": [dataset_id], "name": "x"},
    )
    assert unknown.status_code == 404


def test_cancelling_takes_effect_within_an_epoch(
    env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Found live (doc 96): a SAM 3 epoch stuck in swap could not be cancelled, because the
    # runner only looked between epochs.
    seen: list[int] = []

    def slow_epoch(self, state, data, epoch):  # type: ignore[no-untyped-def]
        for index in range(1000):
            if data.stopped:
                break
            seen.append(index)
            if index == 3:
                job.cancel_requested.set()
            time.sleep(0.001)
        return 1.0

    monkeypatch.setattr(FakeAdapter, "train_epoch", slow_epoch)
    monkeypatch.setattr(
        runner_module,
        "load_data",
        lambda *a, **k: FinetuneData([sample("train")], [sample("val")], [], ("c",)),
    )
    runner = FoundationFinetuneRunner()
    job = runner.submit(
        FinetuneRequest("sam2.1-hiera-small", ("d",), "x", None, FinetuneSettings(epochs=3))
    )
    deadline = time.monotonic() + 10
    while not job.finished and time.monotonic() < deadline:
        time.sleep(0.02)
    assert job.state == "cancelled" and "during epoch 1" in job.message
    assert len(seen) < 10 and job.instance_id is None
