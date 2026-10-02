"""Doc 145: each trained model exported when its training finishes, if switched on."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import Settings
from app.mlops import auto_export


def settings(folder: Path | None) -> Settings:
    return Settings(DINO_MODEL_EXPORT_FOLDER=str(folder) if folder else "")


def test_off_by_default_and_for_a_blank_folder() -> None:
    notes: list[str] = []
    assert auto_export.export_after_training("heads", "h1", notes.append, settings(None)) is None
    assert notes == []


def test_the_bundle_goes_into_the_folder_and_the_job_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written: list[tuple[str, str, Path]] = []

    def export_to(kind: str, instance_id: str, destination: Path) -> Path:
        written.append((kind, instance_id, destination))
        target = destination / f"{instance_id}.zip"
        target.write_bytes(b"zip")
        return target

    monkeypatch.setattr(auto_export, "export_to", export_to)
    notes: list[str] = []
    folder = tmp_path / "models" / "new"  # created when missing
    thread = auto_export.export_after_training("finetuned", "f1", notes.append, settings(folder))
    assert thread is not None
    thread.join(5)
    assert written == [("finetuned", "f1", folder)]
    assert notes == [f"Exported to {folder / 'f1.zip'}"]


def test_a_failed_export_is_a_note_not_a_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_args: Any) -> Path:
        raise ValueError("No weights for h1")

    monkeypatch.setattr(auto_export, "export_to", broken)
    notes: list[str] = []
    thread = auto_export.export_after_training("heads", "h1", notes.append, settings(tmp_path))
    assert thread is not None
    thread.join(5)
    assert notes == [f"The automatic export to {tmp_path} failed: No weights for h1"]


def test_a_head_is_handed_over_when_it_is_saved(monkeypatch: pytest.MonkeyPatch) -> None:
    handed: list[tuple[str, str]] = []
    monkeypatch.setattr(
        auto_export,
        "export_after_training",
        lambda kind, instance_id, _note: handed.append((kind, instance_id)),
    )
    job: Any = SimpleNamespace(listeners=[], notes=[], head_instance_id="h7")
    monkeypatch.setattr(auto_export, "model_folder", lambda: None)
    auto_export._attach(job)
    assert job.listeners == []  # off: nothing listens
    monkeypatch.setattr(auto_export, "model_folder", lambda: Path("/exports"))
    auto_export._attach(job)
    (listen,) = job.listeners
    listen("epoch", job)
    listen("finish", job)
    assert handed == []
    listen("saved", job)
    assert handed == [("heads", "h7")]
    auto_export.install()
    auto_export.install()
    from app.ml.training.job import JOB_HOOKS

    assert JOB_HOOKS.count(auto_export._attach) == 1


def test_the_api_keeps_the_model_folder_unless_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("DINO_ENV_FILE", str(tmp_path / ".env"))
    monkeypatch.delenv("DINO_MODEL_EXPORT_FOLDER", raising=False)
    get_settings.cache_clear()
    client = TestClient(create_app())
    base = {"on_close": True, "every_minutes": 0}
    chosen = client.put(
        "/api/v1/exports/settings", json={**base, "model_folder": str(tmp_path / "m")}
    )
    assert chosen.json()["model_folder"] == str(tmp_path / "m")
    kept = client.put("/api/v1/exports/settings", json={**base, "every_minutes": 5})
    assert kept.json()["model_folder"] == str(tmp_path / "m")  # absent: left as it is
    cleared = client.put("/api/v1/exports/settings", json={**base, "model_folder": None})
    assert cleared.json()["model_folder"] is None
    refused = client.put(
        "/api/v1/exports/settings",
        json={"on_close": False, "every_minutes": 0, "model_folder": "models"},
    )
    assert refused.status_code == 422
    assert client.get("/api/v1/exports/settings").json()["on_close"] is True  # nothing written
    get_settings.cache_clear()
