"""Doc 150: a linked dataset's annotations saved into its bucket, never over a newer save."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cloud import cache, links
from app.cloud.connections import ConnectionRequest, create_connection
from app.cloud.linking import detect_link, import_link
from app.cloud.storage import Storage, memory_storage
from app.datasets.db import transaction
from app.datasets.exchange.auto import run_exports
from app.datasets.exchange.cloud_export import ExportConflict
from app.datasets.exchange.targets import export_to_target, view
from tests import intake_fixtures as fx

DATA = "dinotraining/dinotraining.json"


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.datasets.db import reset_connection

    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_ENV_FILE", str(tmp_path / ".env"))
    get_settings.cache_clear()
    reset_connection()
    links.reset()
    cache.reset()


@pytest.fixture
def bucket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Storage:
    storage = memory_storage("photos")
    monkeypatch.setattr(links, "open_storage", lambda *_args: storage)
    for path in sorted(fx.coco(tmp_path / "rail").rglob("*")):
        if path.is_file():
            storage.put(path.relative_to(tmp_path / "rail").as_posix(), path.read_bytes())
    return storage


def link_bucket() -> str:
    connection = create_connection(
        ConnectionRequest(name="Lab", kind="s3", secrets={"access_key": "a", "secret_key": "b"})
    )
    link, _ = detect_link(connection.id, "photos", "")
    return import_link(link.id, "Rail", None, lambda *_: None).dataset_id


def change(dataset_id: str) -> None:
    with transaction() as connection:
        connection.execute(
            "UPDATE images SET split = 'test' WHERE dataset_id = ? AND annotated_at != ''",
            (dataset_id,),
        )


def keys(storage: Storage) -> list[str]:
    return sorted(entry.key for page in storage.list() for entry in page)


def test_a_linked_dataset_saves_back_into_its_bucket_by_default(bucket: Storage) -> None:
    dataset_id = link_bucket()
    target = view(dataset_id)
    assert (target.kind, target.data_folder, target.linked, target.include_pictures) == (
        "data",
        "s3://photos/dinotraining",
        True,
        False,
    )
    result = export_to_target(dataset_id)
    assert result.folder == "s3://photos/dinotraining" and result.pictures_copied == 0
    assert {"dinotraining/dinotraining.json", "dinotraining/annotations.coco.json"} <= set(
        keys(bucket)
    )
    saved = json.loads(bucket.get(DATA))
    assert sorted(image["path"] for image in saved["tables"]["images"]) == [
        "train/a.jpg",
        "train/b.jpg",
        "train/extra.jpg",
        "valid/c.jpg",
    ]
    assert not view(dataset_id).changed

    change(dataset_id)
    export_to_target(dataset_id)  # an update of its own last export: allowed
    assert {
        image["split"]
        for image in json.loads(bucket.get(DATA))["tables"]["images"]
        if image["annotated_at"]
    } == {"test"}


def test_someone_elses_newer_save_is_never_overwritten(bucket: Storage) -> None:
    from app.main import create_app

    dataset_id = link_bucket()
    export_to_target(dataset_id)
    theirs = b'{"format": "dinotraining-export", "saved by": "a colleague"}'
    bucket.put(DATA, theirs)  # another machine saved meanwhile
    change(dataset_id)
    with pytest.raises(
        ExportConflict,
        match="Nothing was overwritten: yours is at s3://photos/dinotraining/conflicts/",
    ):
        export_to_target(dataset_id)
    assert bucket.get(DATA) == theirs
    copies = [key for key in keys(bucket) if key.startswith("dinotraining/conflicts/")]
    assert len(copies) == 2 and any(key.endswith("dinotraining.json") for key in copies)
    mine = json.loads(bucket.get(next(key for key in copies if key.endswith("dinotraining.json"))))
    assert {image["split"] for image in mine["tables"]["images"] if image["annotated_at"]} == {
        "test"
    }

    reply = TestClient(create_app()).post(f"/api/v1/datasets/{dataset_id}/export")
    assert (
        reply.status_code == 409 and "Nothing was overwritten" in reply.json()["error"]["message"]
    )


def test_a_dataset_restored_from_its_bucket_updates_it_without_a_false_conflict(
    bucket: Storage,
) -> None:
    first = link_bucket()
    export_to_target(first)
    restored = link_bucket()  # linking the bucket again finds this app's export
    with transaction() as connection:
        names = [
            row["name"]
            for row in connection.execute("SELECT name FROM datasets ORDER BY created_at")
        ]
    assert len(names) == 2
    assert not view(restored).changed
    change(restored)
    export_to_target(restored)  # its baseline is the bucket's export: an update
    assert {
        image["split"]
        for image in json.loads(bucket.get(DATA))["tables"]["images"]
        if image["annotated_at"]
    } == {"test"}


def test_closing_the_app_saves_a_changed_linked_dataset_back(bucket: Storage) -> None:
    dataset_id = link_bucket()
    report = run_exports("close")
    assert report is not None and [entry.name for entry in report.exported] == ["Rail"]
    change(dataset_id)
    bucket.put(DATA, b"{}")  # a colleague again
    conflicted = run_exports("close")
    assert conflicted is not None and [entry.name for entry in conflicted.failed] == ["Rail"]
    assert "Nothing was overwritten" in conflicted.failed[0].error


def test_a_german_reader_reads_the_conflict_in_german(bucket: Storage) -> None:
    from app.main import create_app

    dataset_id = link_bucket()
    export_to_target(dataset_id)
    bucket.put(DATA, b"{}")
    change(dataset_id)
    reply = TestClient(create_app()).post(
        f"/api/v1/datasets/{dataset_id}/export", headers={"Accept-Language": "de"}
    )
    assert reply.status_code == 409
    assert reply.json()["error"]["message"].startswith(
        "Jemand anderes hat seit deinem letzten Export Annotationen nach s3://photos/dinotraining"
    )
