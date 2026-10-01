"""A cloud dataset's link (doc 148): which bucket and prefix, and its local cache folder.

A linked picture's path in the database is where it *will* be, `<cache root>/<key>`;
`find` traces such a path back to its bucket key, so doc 149 can fetch it.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from app.cloud.connections import get_connection
from app.cloud.storage import Storage, open_storage
from app.core.config import Settings
from app.datasets.db import data_root, transaction

TABLE = """
CREATE TABLE IF NOT EXISTS cloud_links (
    id            TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL,
    bucket        TEXT NOT NULL,
    prefix        TEXT NOT NULL DEFAULT '',
    cache_root    TEXT NOT NULL,
    dataset_id    TEXT,
    linked_at     TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class Link:
    id: str
    connection_id: str
    bucket: str
    prefix: str
    cache_root: Path
    dataset_id: str | None

    @property
    def uri(self) -> str:
        scheme = {"s3": "s3", "azure": "azure", "gcs": "gs"}[
            get_connection(self.connection_id).kind
        ]
        return f"{scheme}://{self.bucket}/{self.prefix}".rstrip("/")


_lock = threading.Lock()
_storages: dict[str, Storage] = {}
#: The links, read once and kept: `find` runs for every picture an import or a reader opens.
_known: list[Link] | None = None


def _forget() -> None:
    global _known
    with _lock:
        _known = None


def _ensure(settings: Settings | None) -> None:
    with transaction(settings) as connection:
        connection.execute(TABLE)


def cache_path(link: Link, key: str) -> Path:
    """Where a key lives locally; ValueError for a key that would leave the cache."""
    parts = PurePosixPath(key)
    if parts.is_absolute() or ".." in parts.parts or not parts.parts:
        raise ValueError(f"The bucket names a file outside its folder: {key!r}.")
    return link.cache_root.joinpath(*parts.parts)


def create_link(
    connection_id: str, bucket: str, prefix: str, settings: Settings | None = None
) -> Link:
    get_connection(connection_id, settings)  # LookupError for an unknown one
    _ensure(settings)
    link_id = uuid.uuid4().hex[:12]
    root = data_root(settings) / "cloud" / link_id
    root.mkdir(parents=True, exist_ok=True)
    with transaction(settings) as connection:
        connection.execute(
            "INSERT INTO cloud_links (id, connection_id, bucket, prefix, cache_root, linked_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                link_id,
                connection_id,
                bucket,
                prefix.strip("/"),
                str(root),
                datetime.now(UTC).isoformat(timespec="seconds"),
            ),
        )
    _forget()
    return get_link(link_id, settings)


def _from_row(row: dict[str, str | None]) -> Link:
    return Link(
        id=str(row["id"]),
        connection_id=str(row["connection_id"]),
        bucket=str(row["bucket"]),
        prefix=str(row["prefix"] or ""),
        cache_root=Path(str(row["cache_root"])),
        dataset_id=row["dataset_id"],
    )


def get_link(link_id: str, settings: Settings | None = None) -> Link:
    _ensure(settings)
    with transaction(settings) as connection:
        row = connection.execute("SELECT * FROM cloud_links WHERE id = ?", (link_id,)).fetchone()
    if row is None:
        raise LookupError(f"No cloud link {link_id}")
    return _from_row(dict(row))


def all_links(settings: Settings | None = None) -> list[Link]:
    global _known
    with _lock:
        if _known is not None:
            return _known
    _ensure(settings)
    with transaction(settings) as connection:
        rows = connection.execute("SELECT * FROM cloud_links").fetchall()
    links = [_from_row(dict(row)) for row in rows]
    with _lock:
        _known = links
    return links


def set_dataset(link_id: str, dataset_id: str, settings: Settings | None = None) -> None:
    with transaction(settings) as connection:
        connection.execute(
            "UPDATE cloud_links SET dataset_id = ? WHERE id = ?", (dataset_id, link_id)
        )
    _forget()


def delete_link(link_id: str, settings: Settings | None = None) -> None:
    with transaction(settings) as connection:
        connection.execute("DELETE FROM cloud_links WHERE id = ?", (link_id,))
    with _lock:
        _storages.pop(link_id, None)
    _forget()


def find(path: Path, settings: Settings | None = None) -> tuple[Link, str] | None:
    """The link and bucket key behind a cache path, or None for an ordinary file."""
    resolved = path.expanduser()
    for link in all_links(settings):
        if resolved.is_relative_to(link.cache_root):
            return link, resolved.relative_to(link.cache_root).as_posix()
    return None


def storage_for(link: Link, settings: Settings | None = None) -> Storage:
    """One storage per link, built once (credentials read from .env then)."""
    with _lock:
        storage = _storages.get(link.id)
        if storage is None:
            storage = open_storage(
                get_connection(link.connection_id, settings), link.bucket, link.prefix
            )
            _storages[link.id] = storage
        return storage


def reset() -> None:
    """For tests and a changed data folder: forget the links and their storages."""
    global _known
    with _lock:
        _known = None
        _storages.clear()


def forget_storages(connection_id: str) -> None:
    """A connection's endpoint or secrets changed: its links build their storage again."""
    with _lock:
        for link_id in [link.id for link in (_known or []) if link.connection_id == connection_id]:
            _storages.pop(link_id, None)
        if _known is None:
            _storages.clear()  # nothing to tell them apart by: rebuild all, it is cheap
