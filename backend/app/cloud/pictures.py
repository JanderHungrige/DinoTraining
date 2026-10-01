"""Pictures that may still be in the bucket (docs 148, 149): exists, size, fetch.

For an ordinary file these answer exactly as before. For a path inside a cloud link's
cache they ask the bucket: a key listed at linking exists; its size comes from the first
64 KB (PNG and JPEG keep it there); `ensure_local` downloads it into the cache.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
import threading
from collections.abc import Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from app.cloud.cache import fetched, touch
from app.cloud.errors import CloudError
from app.cloud.links import Link, find, storage_for
from app.datasets.db import transaction

logger = logging.getLogger(__name__)

HEADER_BYTES = 64 * 1024
PREFETCH_WORKERS = 8

#: Keys listed while linking (doc 148), so the import's "does it exist" needs no request.
_listed: dict[str, set[str]] = {}
_listed_lock = threading.Lock()


def remember_listing(link_id: str, keys: set[str]) -> None:
    with _listed_lock:
        _listed[link_id] = keys


def picture_exists(path: Path) -> bool:
    if path.is_file():
        return True
    found = find(path)
    if found is None:
        return False
    link, key = found
    with _listed_lock:
        listed = _listed.get(link.id)
    if listed is not None:
        return key in listed
    return storage_for(link).head(key) is not None


def picture_size(path: Path) -> tuple[int, int]:
    """Width and height; OSError when it is no readable picture (as `Image.open`)."""
    if path.is_file():
        with Image.open(path) as opened:
            return opened.size
    found = find(path)
    if found is None:
        raise FileNotFoundError(f"No such picture: {path}")
    link, key = found
    if not picture_exists(path):
        raise FileNotFoundError(f"No such picture in {link.bucket}: {key}")  # as a local one
    storage = storage_for(link)
    # A CloudError (the bucket could not be read) propagates: it must fail the import, not
    # pass as "not a picture", which the importer would skip without a word.
    header = storage.get_range(key, HEADER_BYTES)
    try:
        with Image.open(io.BytesIO(header)) as opened:
            return opened.size
    except (OSError, ValueError):
        pass  # the header was not enough: read the whole picture once
    whole = storage.get(key)
    try:
        with Image.open(io.BytesIO(whole)) as opened:
            return opened.size
    except ValueError as error:
        raise OSError(f"Not a readable picture: {key}") from error


class PictureUnavailableError(FileNotFoundError):
    """A linked picture that is not in the cache and whose bucket cannot be read now."""


_inflight: dict[Path, Future[Path]] = {}
_inflight_lock = threading.Lock()
_prefetcher = ThreadPoolExecutor(max_workers=PREFETCH_WORKERS, thread_name_prefix="prefetch")


def ensure_local(path: Path | str) -> Path:
    """The picture as a local file: an ordinary one at once, a linked one fetched first.

    One download per picture at a time: a reader asking for a picture already being
    fetched (by the prefetcher, say) waits for that fetch.
    """
    path = Path(path)
    if path.is_file():
        if find(path) is not None:
            touch(path)  # recency for the cache's eviction (doc 149)
        return path
    found = find(path)
    if found is None:
        return path  # an ordinary missing file: the caller reports it as before
    with _inflight_lock:
        future = _inflight.get(path)
        mine = future is None
        if mine:
            future = Future()
            _inflight[path] = future
    assert future is not None
    if not mine:
        return future.result()
    try:
        future.set_result(_download(path, *found))
    except BaseException as error:
        future.set_exception(error)
    finally:
        with _inflight_lock:
            _inflight.pop(path, None)
    return future.result()


def _download(path: Path, link: Link, key: str) -> Path:
    try:
        data = storage_for(link).get(key)
    except CloudError as error:
        raise PictureUnavailableError(
            f"{path.name} is not in the cache, and {link.bucket} could not be read: {error}"
        ) from error
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as file:
            file.write(data)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    fetched(len(data))
    logger.debug("Fetched %s from %s", key, link.bucket)
    return path


def prefetch(paths: Iterable[Path | str]) -> int:
    """Fetch linked pictures not yet cached, in the background; returns how many were queued."""
    queued = 0
    for raw in paths:
        path = Path(raw)
        if path.is_file() or find(path) is None:
            continue
        _prefetcher.submit(_quietly, path)
        queued += 1
    return queued


def _quietly(path: Path) -> None:
    try:
        ensure_local(path)
    except (OSError, CloudError) as error:
        logger.info("Prefetch of %s failed: %s", path.name, error)


FOLLOWING = 8


def prefetch_following(path: Path) -> int:
    """Doc 149: the next pictures of a linked dataset, in the Studio's order (by path)."""
    found = find(path)
    if found is None or not found[0].dataset_id:
        return 0
    with transaction() as connection:
        rows = connection.execute(
            "SELECT path FROM images WHERE dataset_id = ? AND path > ? ORDER BY path LIMIT ?",
            (found[0].dataset_id, str(path), FOLLOWING),
        ).fetchall()
    return prefetch(row["path"] for row in rows)
