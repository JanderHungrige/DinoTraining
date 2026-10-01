"""Doc 148: a bucket's dataset detected and imported from its listing, no picture downloaded."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.cloud import links, pictures
from app.cloud.connections import ConnectionRequest, create_connection
from app.cloud.errors import CloudError
from app.cloud.linking import detect_link, import_link
from app.cloud.storage import Storage, memory_storage
from app.datasets.db import transaction
from app.datasets.exchange.export import export_dataset
from app.datasets.intake.importer import run_import
from tests import intake_fixtures as fx

PICTURES = {".jpg", ".png"}


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.datasets.db import reset_connection

    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_ENV_FILE", str(tmp_path / ".env"))
    get_settings.cache_clear()
    reset_connection()
    links.reset()


@pytest.fixture
def buckets(monkeypatch: pytest.MonkeyPatch) -> dict[str, Storage]:
    """In-memory buckets by prefix: what open_storage hands a link."""
    stores: dict[str, Storage] = {}

    def open_storage(_connection: Any, _bucket: str, prefix: str = "") -> Storage:
        return stores.setdefault(prefix, memory_storage(f"photos/{prefix}".rstrip("/")))

    monkeypatch.setattr(links, "open_storage", open_storage)
    return stores


@pytest.fixture
def bucket(buckets: dict[str, Storage]) -> Storage:
    return buckets.setdefault("", memory_storage("photos"))


def upload(storage: Storage, folder: Path, under: str = "") -> None:
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            storage.put(f"{under}{path.relative_to(folder).as_posix()}", path.read_bytes())


def connection() -> str:
    return create_connection(
        ConnectionRequest(name="Lab", kind="s3", secrets={"access_key": "a", "secret_key": "b"})
    ).id


def cached_pictures(link_root: Path) -> list[Path]:
    return [p for p in link_root.rglob("*") if p.suffix.lower() in PICTURES]


def test_a_coco_bucket_links_without_downloading_a_picture(tmp_path: Path, bucket: Storage) -> None:
    upload(bucket, fx.coco(tmp_path / "rail"))
    link, detection = detect_link(connection(), "photos", "")
    assert (detection.kind, detection.pictures, detection.annotated_pictures) == ("coco", 4, 3)
    assert detection.path == "s3://photos"
    assert cached_pictures(link.cache_root) == []  # only the annotation files came down
    result = import_link(link.id, "Rail (cloud)", None, lambda *_: None)
    assert (result.pictures, result.annotated_pictures, result.masks) == (4, 3, 2)
    assert cached_pictures(link.cache_root) == []
    with transaction() as db:
        source = db.execute(
            "SELECT source FROM datasets WHERE id = ?", (result.dataset_id,)
        ).fetchone()
        paths = [
            row["path"]
            for row in db.execute(
                "SELECT path FROM images WHERE dataset_id = ?", (result.dataset_id,)
            )
        ]
    assert source["source"] == "s3://photos"
    assert all(Path(path).is_relative_to(link.cache_root) for path in paths)
    assert links.get_link(link.id).dataset_id == result.dataset_id


def test_yolo_and_plain_pictures_take_their_sizes_from_the_header(
    tmp_path: Path, buckets: dict[str, Storage]
) -> None:
    upload(buckets.setdefault("cars", memory_storage("photos/cars")), fx.yolo(tmp_path / "cars"))
    upload(
        buckets.setdefault("raw", memory_storage("photos/raw")), fx.pictures_only(tmp_path / "raw")
    )
    upload(buckets.setdefault("voc", memory_storage("photos/voc")), fx.voc(tmp_path / "voc"))
    for prefix, expected in (("cars", (3, 3)), ("raw", (3, 0)), ("voc", (1, 1))):
        link, detection = detect_link(connection(), "photos", prefix)
        result = import_link(link.id, prefix, None, lambda *_: None)
        assert (result.pictures, result.annotated_pictures) == expected
        with transaction() as db:
            sizes = {
                (row["width"], row["height"])
                for row in db.execute(
                    "SELECT width, height FROM images WHERE dataset_id = ?", (result.dataset_id,)
                )
            }
        assert sizes == {(fx.W, fx.H)}
        assert cached_pictures(link.cache_root) == []


def test_a_bucket_error_fails_the_import_instead_of_skipping_pictures(
    tmp_path: Path, bucket: Storage, monkeypatch: pytest.MonkeyPatch
) -> None:
    upload(bucket, fx.pictures_only(tmp_path / "raw"))
    link, _ = detect_link(connection(), "photos", "")

    def offline(*_args: Any) -> bytes:
        raise CloudError("The storage could not be reached.")

    monkeypatch.setattr(bucket, "get_range", offline)
    with pytest.raises(CloudError):
        import_link(link.id, "raw", None, lambda *_: None)


def test_a_key_leaving_the_cache_is_refused(bucket: Storage) -> None:
    """obstore refuses such keys itself; the cache path refuses them again, in case a
    provider ever hands one over."""
    link = links.create_link(connection(), "photos", "")
    for key in ("../evil.json", "/etc/passwd", "a/../../b"):
        with pytest.raises(ValueError, match="outside its folder"):
            links.cache_path(link, key)
    assert links.cache_path(link, "a/b.jpg") == link.cache_root / "a" / "b.jpg"


def test_an_export_in_the_bucket_is_restored_completely(tmp_path: Path, bucket: Storage) -> None:
    local = run_import(fx.coco(tmp_path / "rail"), "Rail", "kept", False).dataset_id
    export_dataset(local, tmp_path / "rail")
    upload(bucket, tmp_path / "rail")
    link, detection = detect_link(connection(), "photos", "")
    assert detection.kind == "dinotraining" and detection.notes == []
    restored = import_link(link.id, "", None, lambda *_: None)
    assert (restored.pictures, restored.annotated_pictures) == (4, 3)
    assert cached_pictures(link.cache_root) == []


def test_the_picture_helpers_answer_for_a_cache_path(tmp_path: Path, bucket: Storage) -> None:
    upload(bucket, fx.pictures_only(tmp_path / "raw"))
    link, _ = detect_link(connection(), "photos", "")
    picture = link.cache_root / "p0.png"
    assert pictures.picture_exists(picture) and not pictures.picture_exists(
        link.cache_root / "nope.png"
    )
    assert pictures.picture_size(picture) == (fx.W, fx.H)
    assert not picture.exists()
    assert (
        pictures.ensure_local(picture) == picture
        and picture.read_bytes() == (tmp_path / "raw/p0.png").read_bytes()
    )
    ordinary = tmp_path / "ordinary.png"
    assert pictures.ensure_local(ordinary) == ordinary and not pictures.picture_exists(ordinary)


def test_the_api_detects_links_and_refuses(tmp_path: Path, bucket: Storage) -> None:
    from app.main import create_app

    upload(bucket, fx.coco(tmp_path / "rail"))
    client = TestClient(create_app())
    found = client.post(
        "/api/v1/cloud/links/detect", json={"connection_id": connection(), "bucket": "photos"}
    )
    assert found.status_code == 200 and found.json()["detection"]["kind"] == "coco"
    started = client.post(
        "/api/v1/cloud/links", json={"link_id": found.json()["link_id"], "name": "Rail"}
    )
    assert started.status_code == 202
    job_id = started.json()["job_id"]
    import time

    for _ in range(100):
        job = client.get(f"/api/v1/datasets/import/jobs/{job_id}").json()
        if job["state"] != "running":
            break
        time.sleep(0.05)
    assert job["state"] == "complete", job
    assert (
        client.post(
            "/api/v1/cloud/links/detect", json={"connection_id": "nope", "bucket": "b"}
        ).status_code
        == 404
    )
    assert client.post("/api/v1/cloud/links", json={"link_id": "nope"}).status_code == 404
