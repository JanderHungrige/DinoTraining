"""Doc 149: linked pictures fetched when needed, once, a batch ahead, in a bounded cache."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.cloud import cache, links, pictures
from app.cloud.connections import ConnectionRequest, create_connection
from app.cloud.errors import explain
from app.cloud.linking import detect_link, import_link
from app.cloud.storage import Storage, memory_storage
from app.datasets.db import transaction
from app.ml.images import read_image
from app.ml.training.loop import load_image
from tests import intake_fixtures as fx


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
    for path in sorted(fx.pictures_only(tmp_path / "raw").rglob("*")):
        storage.put(path.name, path.read_bytes())
    return storage


def linked(bucket: Storage) -> list[Path]:
    """A linked dataset of three pictures, none cached; their cache paths."""
    connection = create_connection(
        ConnectionRequest(name="Lab", kind="s3", secrets={"access_key": "a", "secret_key": "b"})
    )
    link, _ = detect_link(connection.id, "photos", "")
    result = import_link(link.id, "raw", None, lambda *_: None)
    with transaction() as db:
        rows = db.execute(
            "SELECT path FROM images WHERE dataset_id = ? ORDER BY path", (result.dataset_id,)
        ).fetchall()
    return [Path(row["path"]) for row in rows]


def wait_for(condition: Any, seconds: float = 5) -> None:
    deadline = time.monotonic() + seconds
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.02)


def test_every_reader_gets_the_picture_fetched_first(bucket: Storage) -> None:
    first, second, third = linked(bucket)
    image, resolved = read_image(str(first))  # the Studio, inference, the Generator
    assert resolved == first and first.is_file() and image.size == (fx.W, fx.H)
    assert load_image(str(second)) is not None and second.is_file()  # training
    assert not third.exists()  # nothing fetched that nobody asked for


def test_one_download_per_picture_however_many_ask(
    bucket: Storage, monkeypatch: pytest.MonkeyPatch
) -> None:
    (first, *_rest) = linked(bucket)
    calls: list[str] = []
    original = bucket.get

    def slow_get(key: str) -> bytes:
        calls.append(key)
        time.sleep(0.2)
        return original(key)

    monkeypatch.setattr(bucket, "get", slow_get)
    threads = [threading.Thread(target=pictures.ensure_local, args=(first,)) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert calls == ["p0.png"] and first.is_file()


def test_an_unreachable_bucket_makes_the_picture_unavailable_with_a_reason(
    bucket: Storage, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.main import create_app

    first, second, _ = linked(bucket)
    pictures.ensure_local(first)  # cached before going offline

    def offline(_key: str) -> bytes:
        raise explain(RuntimeError("error sending request"), "photos")  # what obstore gives

    monkeypatch.setattr(bucket, "get", offline)
    assert read_image(str(first))[1] == first  # the cache still serves it
    with pytest.raises(
        pictures.PictureUnavailableError, match="not in the cache, and photos could not be read"
    ):
        pictures.ensure_local(second)
    assert load_image(str(second)) is None  # training skips it with a warning
    reply = TestClient(create_app()).get("/api/v1/annotate/image", params={"path": str(second)})
    assert reply.status_code == 404 and "could not be read" in reply.json()["error"]["message"]
    german = TestClient(create_app()).get(
        "/api/v1/annotate/image", params={"path": str(second)}, headers={"Accept-Language": "de"}
    )
    message = german.json()["error"]["message"]
    assert message.startswith(
        "p1.png liegt nicht im Cache, und photos konnte nicht gelesen werden:"
    )
    assert "Der Speicher war nicht erreichbar" in message


def test_the_cache_keeps_its_bound_and_drops_the_least_recently_used(
    bucket: Storage, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second, third = linked(bucket)
    size = len(bucket.get("p0.png"))
    monkeypatch.setattr(cache, "bound_bytes", lambda settings=None: int(size * 2.5))
    pictures.ensure_local(first)
    pictures.ensure_local(second)
    os.utime(first, (time.time() - 100, time.time() - 100))
    os.utime(second, (time.time() - 50, time.time() - 50))
    pictures.ensure_local(first)  # read again: now the most recent
    pictures.ensure_local(third)  # over the bound: the least recently used goes
    assert first.is_file() and third.is_file() and not second.exists()
    assert cache.used_bytes() <= int(size * 2.5)
    assert (first.parent / "p0.png").exists()


def test_prefetching_runs_ahead_and_the_studio_asks_for_the_next(bucket: Storage) -> None:
    first, second, third = linked(bucket)
    assert pictures.prefetch_following(first) == 2  # the two after it, by path
    wait_for(lambda: second.is_file() and third.is_file())
    assert pictures.prefetch([first, second, third]) == 1  # only what is not cached


def test_links_without_a_dataset_are_cleaned_up_at_start(bucket: Storage) -> None:
    kept_paths = linked(bucket)
    connection = links.all_links()[0].connection_id
    orphan, _ = detect_link(connection, "photos", "")  # checked, never linked
    assert orphan.cache_root.is_dir()
    assert cache.clean_up_links() == 1
    assert not orphan.cache_root.exists()
    assert [link.dataset_id is not None for link in links.all_links()] == [True]
    assert kept_paths[0].parent.is_dir()


def test_the_api_reports_bounds_and_empties_the_cache(bucket: Storage, tmp_path: Path) -> None:
    from app.main import create_app

    first, *_ = linked(bucket)
    pictures.ensure_local(first)
    client = TestClient(create_app())
    state = client.get("/api/v1/cloud/cache").json()
    assert state["bound_gb"] == 5.0 and state["used_bytes"] > 0
    assert [(entry["pictures"], entry["cached"]) for entry in state["datasets"]] == [(3, 1)]
    assert client.put("/api/v1/cloud/cache", json={"bound_gb": 2}).json()["bound_gb"] == 2.0
    assert "DINO_CLOUD_CACHE_GB=2" in (tmp_path / ".env").read_text()
    emptied = client.post("/api/v1/cloud/cache/clear").json()
    assert emptied["used_bytes"] == 0 and not first.exists()
    assert client.put("/api/v1/cloud/cache", json={"bound_gb": 0}).status_code == 422


def test_a_changed_connection_reaches_its_linked_datasets_at_once(
    bucket: Storage, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second, _ = linked(bucket)
    link = links.all_links()[0]
    assert links.storage_for(link) is bucket
    replacement = memory_storage("photos")
    replacement.put("p0.png", bucket.get("p0.png"))
    monkeypatch.setattr(links, "open_storage", lambda *_args: replacement)
    assert links.storage_for(link) is bucket  # kept until told
    links.forget_storages(link.connection_id)
    assert links.storage_for(link) is replacement
