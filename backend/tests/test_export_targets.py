"""Doc 143: where a dataset's export goes, remembered, and whether it changed since."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.datasets.db import transaction
from app.datasets.exchange.targets import Target, export_to_target, set_target, view
from app.datasets.intake.importer import run_import
from app.datasets.store import dataset_dir
from tests import intake_fixtures as fx


@pytest.fixture(autouse=True)
def _data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.datasets.db import reset_connection

    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_connection()


def test_with_the_data_is_offered_for_pictures_outside_the_app_only(tmp_path: Path) -> None:
    in_place = run_import(fx.coco(tmp_path / "rail"), "Rail", None, False).dataset_id
    copied = run_import(fx.voc(tmp_path / "v"), "Dogs", None, True).dataset_id
    first = view(in_place)
    assert first.data_folder == str(tmp_path / "rail") and first.kind is None
    assert first.changed and first.exported_at is None and not first.include_pictures
    second = view(copied)
    assert second.data_folder is None and second.include_pictures  # copy them by default
    with pytest.raises(ValueError, match="live inside the app"):
        set_target(copied, Target(kind="data"))
    with pytest.raises(ValueError, match="Choose the folder"):
        set_target(copied, Target(kind="folder", folder=" "))


def test_an_export_is_remembered_and_any_change_shows(tmp_path: Path) -> None:
    dataset_id = run_import(fx.coco(tmp_path / "rail"), "Rail", None, False).dataset_id
    with pytest.raises(ValueError, match="no export target"):
        export_to_target(dataset_id)
    set_target(dataset_id, Target(kind="data"))
    result = export_to_target(dataset_id)
    assert result.folder == str(tmp_path / "rail" / "v-rex")
    after = view(dataset_id)
    assert after.kind == "data" and after.exported_folder == result.folder
    assert not after.changed  # exported just now; the bookkeeping itself is no change

    with transaction() as connection:  # a phrase's variants: no picture is touched
        connection.execute(
            "INSERT INTO phrases (dataset_id, text, class_name, created_at)"
            " VALUES (?, 'signal', 'signal', 't')",
            (dataset_id,),
        )
    assert view(dataset_id).changed
    export_to_target(dataset_id)
    (dataset_dir(dataset_id) / "guideline.md").write_text("Box the whole signal.")
    assert view(dataset_id).changed  # a state file counts too


def test_the_api_chooses_exports_and_lists_the_last_export(tmp_path: Path) -> None:
    from app.main import create_app

    client = TestClient(create_app())
    dataset_id = run_import(fx.coco(tmp_path / "rail"), "Rail", None, False).dataset_id
    base = f"/api/v1/datasets/{dataset_id}/export"
    assert client.post(base).status_code == 422  # nothing chosen yet

    chosen = client.put(f"{base}/target", json={"kind": "folder", "folder": str(tmp_path / "out")})
    assert chosen.status_code == 200 and chosen.json()["folder"] == str(tmp_path / "out")
    written = client.post(base)
    assert written.status_code == 200 and written.json()["folder"] == str(tmp_path / "out/v-rex")
    profile = client.get(f"/api/v1/datasets/{dataset_id}/profile").json()
    assert profile["exported_folder"] == str(tmp_path / "out/v-rex") and profile["exported_at"]

    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    refused = client.post(base, json={"target": str(blocker)})
    assert refused.status_code == 422
    assert client.get(f"{base}/target").json()["folder"] == str(tmp_path / "out")  # not remembered

    bad = client.put(f"{base}/target", json={"kind": "elsewhere"})
    assert bad.status_code == 422
    assert client.get("/api/v1/datasets/nope/export/target").status_code == 404


def test_a_restore_does_not_inherit_the_originals_export(tmp_path: Path) -> None:
    dataset_id = run_import(fx.coco(tmp_path / "rail"), "Rail", None, False).dataset_id
    set_target(dataset_id, Target(kind="data"))
    export_to_target(dataset_id)
    shutil.move(tmp_path / "rail", tmp_path / "moved")
    restored = run_import(tmp_path / "moved", "", None, False).dataset_id
    again = view(restored)
    assert again.kind is None and again.exported_at is None and again.changed
