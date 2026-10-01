"""Sending the models trained before (doc 124): each once, with its history."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import torch

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.ml.foundation.instances import FoundationInstanceStore
from app.ml.heads.store import HeadInstanceStore
from app.mlops import backfill
from app.mlops.backfill import BackfillJob


class FakeMlflow:
    def __init__(self) -> None:
        self.runs: dict[str, dict[str, Any]] = {}

    def experiment_id(self, name: str) -> str:
        return "1"

    def search_runs(self, experiment: str, tag: str, value: str) -> list[str]:
        return [rid for rid, run in self.runs.items() if run["tags"].get(tag) == value]

    def create_run(
        self, experiment: str, name: str, tags: dict[str, str], start_ms: int | None = None
    ) -> tuple[str, str]:
        rid = f"r{len(self.runs) + 1}"
        self.runs[rid] = {
            "name": name,
            "tags": dict(tags),
            "metrics": [],
            "start": start_ms,
            "files": [],
        }
        return rid, f"mlflow-artifacts:/1/{rid}/artifacts"

    def log_params(self, run_id: str, params: dict[str, str]) -> None:
        self.runs[run_id]["params"] = params

    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int) -> None:
        self.runs[run_id]["metrics"].append((step, metrics))

    def upload(self, artifacts: str, path: str, data: bytes) -> None:
        self.runs[artifacts.split("/")[2]]["files"].append(path)

    def set_tag(self, run_id: str, key: str, value: str) -> None:
        self.runs[run_id]["tags"][key] = value

    def register(self, name: str, run_id: str, path: str = "model") -> str:
        return "1"

    def end_run(self, run_id: str, status: str) -> None:
        self.runs[run_id]["status"] = status


@pytest.fixture
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeMlflow]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow.test")
    get_settings.cache_clear()
    reset_connection()
    fake = FakeMlflow()
    monkeypatch.setattr(backfill, "MlflowClient", lambda _settings: fake)
    store = HeadInstanceStore()
    common: dict[str, Any] = {
        "task": "classification",
        "backbone_id": "dinov2-small",
        "backbone_family": "dinov2",
        "embed_dim": 384,
        "weights": {"linear.weight": torch.zeros(2, 384)},
    }
    epochs = [
        {"epoch": 1, "train_loss": 0.7, "val_loss": 0.8, "metrics": {"accuracy": 0.6}},
        {"epoch": 2, "train_loss": 0.4, "val_loss": 0.5, "metrics": {"accuracy": 0.9}},
    ]
    store.register(
        name="Screws: m8",
        kind="trained-here",
        head_type_id="linear-classifier",
        num_classes=2,
        class_names=("m8", "m9"),
        metrics={"accuracy": 0.9},
        epochs_trained=2,
        history=epochs,
        **common,
    )
    store.register(
        name="ImageNet",
        kind="pretrained-default",
        head_type_id="linear-classifier",
        num_classes=2,
        **common,
    )
    FoundationInstanceStore().save(
        existing_id=None, name="outlines", base_model_id="sam2.1-hiera-small", dataset_ids=(),
        class_names=("ring",), metrics={"miou": 0.9}, epochs_trained=3,
        save=lambda d: (d / "w.safetensors").write_bytes(b"w"), baseline_metrics={"miou": 0.8},
    )  # fmt: skip
    yield fake
    reset_connection()
    get_settings.cache_clear()


def _run() -> BackfillJob:
    job = BackfillJob(job_id="b1")
    backfill._run(job)
    return job


def test_sends_every_model_trained_here_once(library: FakeMlflow) -> None:
    job = _run()
    assert (job.state, job.sent, job.skipped, job.failed) == ("complete", 2, 1, 0)
    head = next(run for run in library.runs.values() if run["tags"]["dinotraining.kind"] == "head")
    assert [step for step, _ in head["metrics"]] == [1, 2, 2]  # each epoch, then the finals
    assert head["tags"]["dinotraining.backfilled"] == "true"
    assert head["status"] == "FINISHED" and head["start"] is not None
    assert {"model/model.json"} <= set(head["files"])
    tuned = next(
        run for run in library.runs.values() if run["tags"]["dinotraining.kind"] == "finetuned"
    )
    assert tuned["metrics"] == [(3, {"miou": 0.9, "baseline_miou": 0.8})]


def test_pressing_it_again_sends_nothing_twice(library: FakeMlflow) -> None:
    _run()
    again = _run()
    assert (again.sent, again.skipped) == (0, 3)
    assert len(library.runs) == 2
