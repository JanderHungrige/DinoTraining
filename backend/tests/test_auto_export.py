"""Doc 144: exporting every changed dataset, on closing, by interval, on demand."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.datasets.db import transaction
from app.datasets.exchange import auto
from app.datasets.exchange.auto import last_report, run_exports
from app.datasets.exchange.targets import Target, set_target
from app.datasets.intake.importer import run_import
from tests import intake_fixtures as fx


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.datasets.db import reset_connection

    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_ENV_FILE", str(tmp_path / ".env"))
    monkeypatch.delenv("DINO_EXPORT_ON_CLOSE", raising=False)
    monkeypatch.delenv("DINO_EXPORT_EVERY_MINUTES", raising=False)
    get_settings.cache_clear()
    reset_connection()


def two_datasets(tmp_path: Path) -> tuple[str, str]:
    targeted = run_import(fx.coco(tmp_path / "rail"), "Rail", None, False).dataset_id
    set_target(targeted, Target(kind="data"))
    untargeted = run_import(fx.yolo(tmp_path / "cars"), "Cars", None, False).dataset_id
    return targeted, untargeted


def test_only_what_changed_goes_and_datasets_without_a_target_are_named(tmp_path: Path) -> None:
    targeted, _ = two_datasets(tmp_path)
    first = run_exports("manual")
    assert first is not None
    assert [entry.name for entry in first.exported] == ["Rail"]
    assert [entry.name for entry in first.no_target] == ["Cars"]
    assert (tmp_path / "rail/dinotraining/dinotraining.json").is_file()

    second = run_exports("interval")
    assert second is not None and second.exported == [] and second.unchanged == 1

    with transaction() as connection:
        connection.execute(
            "UPDATE images SET split = 'test' WHERE dataset_id = ? AND annotated_at != ''",
            (targeted,),
        )
    third = run_exports("close")
    assert third is not None and [entry.name for entry in third.exported] == ["Rail"]
    kept = last_report()
    assert kept is not None and kept.reason == "close" and kept.finished_at


def test_a_deadline_leaves_the_rest_for_the_next_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_import(fx.coco(tmp_path / "a"), "A", None, False)
    run_import(fx.coco(tmp_path / "b"), "B", None, False)
    for info_id in [row["id"] for row in _all_ids()]:
        set_target(info_id, Target(kind="data"))
    clock = iter([0.0, 5.0, 20.0])  # the deadline is 10: A starts, B would start after it
    monkeypatch.setattr("app.datasets.exchange.auto.time.monotonic", lambda: next(clock))
    report = run_exports("close", deadline_seconds=10)
    assert report is not None
    assert [entry.name for entry in report.exported] == ["A"]
    assert [entry.name for entry in report.unfinished] == ["B"]


def _all_ids() -> list:  # type: ignore[type-arg]
    with transaction() as connection:
        return connection.execute("SELECT id FROM datasets ORDER BY created_at").fetchall()


def test_a_failed_target_is_reported_and_the_others_still_go(tmp_path: Path) -> None:
    broken = run_import(fx.coco(tmp_path / "a"), "Broken", None, False).dataset_id
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    set_target(broken, Target(kind="folder", folder=str(blocker)))
    fine = run_import(fx.coco(tmp_path / "b"), "Fine", None, False).dataset_id
    set_target(fine, Target(kind="data"))
    report = run_exports("manual")
    assert report is not None
    assert [entry.name for entry in report.failed] == [
        "Broken"
    ] and "Cannot write" in report.failed[0].error
    assert [entry.name for entry in report.exported] == ["Fine"]


def test_one_run_at_a_time(tmp_path: Path) -> None:
    two_datasets(tmp_path)
    assert auto._lock.acquire(blocking=False)
    try:
        assert run_exports("manual") is None
        assert not auto.start_in_background("interval")
    finally:
        auto._lock.release()


def test_the_api_settings_closing_and_status(tmp_path: Path) -> None:
    from app.main import create_app

    two_datasets(tmp_path)
    client = TestClient(create_app())
    assert client.get("/api/v1/exports/settings").json() == {"on_close": True, "every_minutes": 0}
    saved = client.put("/api/v1/exports/settings", json={"on_close": False, "every_minutes": 10})
    assert saved.json() == {"on_close": False, "every_minutes": 10}
    assert "DINO_EXPORT_EVERY_MINUTES=10" in (tmp_path / ".env").read_text()
    assert (
        client.post("/api/v1/exports/run", json={"reason": "close", "deadline_seconds": 20}).json()[
            "outcome"
        ]
        == "off"
    )

    client.put("/api/v1/exports/settings", json={"on_close": True, "every_minutes": 0})
    closing = client.post(
        "/api/v1/exports/run", json={"reason": "close", "deadline_seconds": 20}
    ).json()
    assert closing["outcome"] == "done" and [
        entry["name"] for entry in closing["report"]["exported"]
    ] == ["Rail"]
    status = client.get("/api/v1/exports/status").json()
    assert status["running"] is False and status["last"]["reason"] == "close"
    assert (
        client.put(
            "/api/v1/exports/settings", json={"on_close": True, "every_minutes": 5000}
        ).status_code
        == 422
    )
    assert client.post("/api/v1/exports/run", json={"reason": "whenever"}).status_code == 422
