"""Doc 142: a dataset's complete export, and its restore by importing the folder."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.datasets.db import transaction
from app.datasets.exchange import layout
from app.datasets.exchange.dump import TABLES, dump_dataset
from app.datasets.exchange.export import export_dataset
from app.datasets.intake.detect import scan
from app.datasets.intake.importer import run_import
from app.datasets.store import DatasetStore, dataset_dir
from tests import intake_fixtures as fx


@pytest.fixture(autouse=True)
def _data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.datasets.db import reset_connection

    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_connection()


def rich_dataset(root: Path) -> str:
    """Doc 136's COCO import (boxes, masks, a never-saved picture, splits), plus what only
    this app knows: classes, phrases with variants, an umbrella term, a mask's phrase,
    per-picture checks, an excluded picture, a frame, the guideline and a recipe."""
    dataset_id = run_import(fx.coco(root), "Rail", "Signals near Hamburg", False).dataset_id
    with transaction() as connection:
        image = connection.execute(
            "SELECT id FROM images WHERE dataset_id = ? ORDER BY path LIMIT 1", (dataset_id,)
        ).fetchone()["id"]
        mask = connection.execute(
            "SELECT m.id FROM masks m JOIN images i ON i.id = m.image_id"
            " WHERE i.dataset_id = ? LIMIT 1",
            (dataset_id,),
        ).fetchone()["id"]
        connection.execute(
            "INSERT INTO dataset_classes (dataset_id, name, created_at) VALUES (?, 'signal', 't0')",
            (dataset_id,),
        )
        cursor = connection.execute(
            "INSERT INTO phrases (dataset_id, text, class_name, variants, confusable, created_at)"
            " VALUES (?, 'person', 'person', '[\"pedestrian\"]', '[\"pole\"]', 't1')",
            (dataset_id,),
        )
        person = cursor.lastrowid
        umbrella = connection.execute(
            "INSERT INTO phrases (dataset_id, text, class_name, created_at)"
            " VALUES (?, 'thing', '', 't2')",
            (dataset_id,),
        ).lastrowid
        connection.execute(
            "INSERT INTO phrase_classes VALUES (?, 'signal'), (?, 'person')", (umbrella, umbrella)
        )
        connection.execute("INSERT INTO mask_phrases VALUES (?, ?)", (mask, person))
        connection.execute(
            "INSERT INTO image_phrase_status VALUES (?, ?, 'absent')", (image, person)
        )
        connection.execute(
            "UPDATE images SET excluded = 1, sequence = 'clip', frame_index = 7 WHERE id = ?",
            (image,),
        )
    folder = dataset_dir(dataset_id)
    (folder / "guideline.md").write_text("Box the whole signal.", encoding="utf-8")
    (folder / "recipes").mkdir(exist_ok=True)
    (folder / "recipes" / "r1.json").write_text(json.dumps({"id": "r1", "dataset_id": dataset_id}))
    return dataset_id


def canonical(dump: dict[str, Any]) -> dict[str, Any]:
    """Tables with ids replaced by positions, so two dumps of one dataset compare equal."""
    positions: dict[str, dict[int, int]] = {}
    out: dict[str, Any] = {}
    for table in TABLES:
        rows = dump["tables"][table.name]
        if table.keyed:
            positions[table.name] = {row["id"]: index for index, row in enumerate(rows)}
        out[table.name] = [
            {
                key: positions[dict(table.refs)[key]][value] if key in dict(table.refs) else value
                for key, value in row.items()
                if key != "id"
            }
            for row in rows
        ]
    return out


def test_an_export_moved_elsewhere_restores_every_row_and_file(tmp_path: Path) -> None:
    original = rich_dataset(tmp_path / "rail")
    result = export_dataset(original, tmp_path / "rail")  # "with the data"
    assert Path(result.folder) == tmp_path / "rail" / "dinotraining"
    assert (result.pictures, result.annotated) == (4, 3)
    coco = json.loads((tmp_path / "rail/dinotraining/annotations.coco.json").read_text())
    assert sorted(image["file_name"] for image in coco["images"]) == [
        "train/a.jpg",
        "train/b.jpg",
        "valid/c.jpg",
    ]

    shutil.move(tmp_path / "rail", tmp_path / "moved")  # another place, another machine
    detection, _, _ = scan(tmp_path / "moved")
    assert detection.kind == "dinotraining" and detection.notes == []  # before its old COCO files
    assert (detection.pictures, detection.annotated_pictures) == (4, 3)
    restored = run_import(tmp_path / "moved", "", "restored here", False)

    before = json.loads((tmp_path / "moved/dinotraining/dinotraining.json").read_text())
    after = dump_dataset(restored.dataset_id)
    assert canonical(after) == canonical(before)
    assert after["pictures_root"] == str(tmp_path / "moved")
    assert after["dataset"]["name"] == "Rail" and after["dataset"]["description"] == "restored here"
    assert after["files"]["guideline.md"] == "Box the whole signal."
    recipe = json.loads(after["files"]["recipes/r1.json"])
    assert recipe["dataset_id"] == restored.dataset_id  # rewritten for the new dataset
    assert restored.classes == ["person", "signal"]


def test_copied_pictures_restore_without_the_originals(tmp_path: Path) -> None:
    original = rich_dataset(tmp_path / "rail")
    export_dataset(original, tmp_path / "backup", include_pictures=True)
    shutil.rmtree(tmp_path / "rail")
    assert (tmp_path / "backup/dinotraining/pictures/train/a.jpg").is_file()
    restored = run_import(tmp_path / "backup", "", None, False)
    dump = dump_dataset(restored.dataset_id)
    assert dump["pictures_root"] == str(tmp_path / "backup/dinotraining/pictures")
    assert all(
        Path(dump["pictures_root"], image["path"]).is_file() for image in dump["tables"]["images"]
    )


def test_missing_pictures_are_named_and_nothing_is_left(tmp_path: Path) -> None:
    original = rich_dataset(tmp_path / "rail")
    export_dataset(original, tmp_path / "backup")
    shutil.rmtree(tmp_path / "rail")
    detection, _, _ = scan(tmp_path / "backup")
    assert detection.notes == ["export-pictures-missing"]
    with pytest.raises(ValueError, match="were not found"):
        run_import(tmp_path / "backup", "", None, False)
    assert [info.id for info in DatasetStore().list_all()] == [original]


def test_damaged_newer_and_escaping_exports_are_refused(tmp_path: Path) -> None:
    original = rich_dataset(tmp_path / "rail")
    export_dataset(original, tmp_path / "rail")
    data = tmp_path / "rail/dinotraining/dinotraining.json"
    dump = json.loads(data.read_text())

    newer = {**dump, "version": 99}
    data.write_text(json.dumps(newer))
    with pytest.raises(ValueError, match="newer DinoTraining"):
        scan(tmp_path / "rail")

    escaping = json.loads(json.dumps(dump))
    escaping["tables"]["images"][1]["path"] = "../../etc/passwd"
    data.write_text(json.dumps(escaping))
    with pytest.raises(ValueError, match="outside its folder"):
        run_import(tmp_path / "rail", "", None, False)

    future = json.loads(json.dumps(dump))
    future["tables"]["boxes"][0]["sparkle"] = 1  # a column from a later version
    data.write_text(json.dumps(future))
    assert run_import(tmp_path / "rail", "", None, False).objects == len(
        dump["tables"]["boxes"]
    ) + len(dump["tables"]["masks"])
    assert len(DatasetStore().list_all()) == 2  # the escaping one left nothing


def test_an_interrupted_write_keeps_the_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "x.json"
    layout.write_atomically(target, "old")

    def broken(*_args: object) -> None:
        raise OSError("disk gone")

    monkeypatch.setattr("app.datasets.exchange.layout.os.replace", broken)
    with pytest.raises(OSError):
        layout.write_atomically(target, "new")
    assert target.read_text() == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["x.json"]  # no temporary left


def test_the_api_exports_and_says_why_not(tmp_path: Path) -> None:
    from app.main import create_app

    original = rich_dataset(tmp_path / "rail")
    client = TestClient(create_app())
    reply = client.post(
        f"/api/v1/datasets/{original}/export", json={"target": str(tmp_path / "out")}
    )
    assert reply.status_code == 200 and reply.json()["objects"] > 0
    assert (tmp_path / "out/dinotraining/dinotraining.json").is_file()
    assert (
        client.post("/api/v1/datasets/nope/export", json={"target": str(tmp_path)}).status_code
        == 404
    )
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    reply = client.post(f"/api/v1/datasets/{original}/export", json={"target": str(blocker)})
    assert reply.status_code == 422 and "Cannot write" in reply.json()["error"]["message"]
