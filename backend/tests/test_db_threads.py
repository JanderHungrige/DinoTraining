"""The shared connection under concurrent threads (found live, 2026-09-30).

FastAPI runs sync handlers in a thread pool, and the audit, training and generator jobs
run on threads of their own. One `sqlite3.Connection` used from several threads at once
fails with "bad parameter or other API misuse", and once answered "Dataset not found" for
a dataset that existed. `transaction()` must serialise units of work.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.datasets.db import reset_connection, transaction
from app.datasets.store import DatasetStore


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[DatasetStore]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_connection()
    yield DatasetStore()
    reset_connection()
    get_settings.cache_clear()


def test_many_threads_share_the_connection_without_misuse(store: DatasetStore) -> None:
    dataset_id = store.create("Threads", None, False).id
    errors: list[BaseException] = []
    missing: list[int] = []

    def work() -> None:
        try:
            for _ in range(300):
                if not store.exists(dataset_id):
                    missing.append(1)
                with transaction() as connection:
                    connection.execute("SELECT COUNT(*) FROM images").fetchone()
        except BaseException as error:  # noqa: BLE001 - collected and asserted below
            errors.append(error)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert missing == []


def test_one_thread_s_rollback_never_undoes_another_s_work(store: DatasetStore) -> None:
    inside = threading.Event()
    proceed = threading.Event()

    def failing() -> None:
        with pytest.raises(RuntimeError), transaction() as connection:
            connection.execute("INSERT INTO datasets (id, name, created_at) VALUES ('x', 'x', '')")
            inside.set()
            proceed.wait(0.5)
            raise RuntimeError("roll back")

    worker = threading.Thread(target=failing)
    worker.start()
    inside.wait(2)
    # Must not be swallowed by the other thread's rollback.
    kept = store.create("Kept", None, False).id
    proceed.set()
    worker.join()
    assert store.exists(kept)
    assert not store.exists("x")
