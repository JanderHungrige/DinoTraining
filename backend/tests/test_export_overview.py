"""Doc 146: what uninstalling now would lose."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.datasets.db import transaction
from app.datasets.exchange.overview import export_overview
from app.datasets.exchange.targets import Target, export_to_target, set_target
from app.datasets.intake.importer import run_import
from tests import intake_fixtures as fx


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.datasets.db import reset_connection

    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_ENV_FILE", str(tmp_path / ".env"))
    monkeypatch.delenv("DINO_MODEL_EXPORT_FOLDER", raising=False)
    get_settings.cache_clear()
    reset_connection()


def test_work_without_a_target_and_changes_after_an_export_are_named(tmp_path: Path) -> None:
    run_import(fx.pictures_only(tmp_path / "raw"), "Raw", None, False)  # nothing saved: no work
    run_import(fx.yolo(tmp_path / "cars"), "Cars", None, False)
    rail = run_import(fx.coco(tmp_path / "rail"), "Rail", None, False).dataset_id
    set_target(rail, Target(kind="data"))
    export_to_target(rail)

    first = export_overview()
    assert (first.datasets, first.no_target, first.unexported) == (2, ["Cars"], [])
    assert first.models == 0 and first.model_folder is None

    with transaction() as connection:
        connection.execute("UPDATE images SET excluded = 1 WHERE dataset_id = ?", (rail,))
    assert export_overview().unexported == ["Rail"]


def test_the_api_answers_the_notice(tmp_path: Path) -> None:
    from app.main import create_app

    run_import(fx.yolo(tmp_path / "cars"), "Cars", None, False)
    reply = TestClient(create_app()).get("/api/v1/exports/overview")
    assert reply.status_code == 200
    assert reply.json() == {
        "datasets": 1,
        "no_target": ["Cars"],
        "unexported": [],
        "models": 0,
        "model_folder": None,
    }
