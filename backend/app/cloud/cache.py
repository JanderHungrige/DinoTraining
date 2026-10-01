"""The linked pictures' local cache (doc 149): bounded, least recently used first.

`DINO_CLOUD_CACHE_GB` bounds the pictures in every link's cache together; annotation
files neither count nor go. Reading a cached picture touches it; a fetch that takes the
cache over its bound evicts the oldest pictures down to 90 % of it.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path

from app.cloud.links import Link, all_links, delete_link
from app.core.config import Settings, get_settings
from app.datasets.db import transaction
from app.ml.images import IMAGE_SUFFIXES

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_used: int | None = None


def bound_bytes(settings: Settings | None = None) -> int:
    return int((settings or get_settings()).cloud_cache_gb * 1024**3)


def _pictures(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [
        path for path in root.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES and path.is_file()
    ]


def _all_pictures() -> list[Path]:
    return [picture for link in all_links() for picture in _pictures(link.cache_root)]


def used_bytes() -> int:
    global _used
    with _lock:
        if _used is None:
            _used = sum(path.stat().st_size for path in _all_pictures())
        return _used


def touch(path: Path) -> None:
    """Mark a cached picture as just read (recency for eviction)."""
    try:
        os.utime(path)
    except OSError:
        pass


def fetched(size: int) -> None:
    """Account a new picture; evict when the cache is over its bound."""
    global _used
    used_bytes()
    with _lock:
        assert _used is not None
        _used += size
        over = _used > bound_bytes()
    if over:
        evict(int(bound_bytes() * 0.9))


def evict(target: int) -> int:
    """Remove the least recently used pictures until the cache holds `target` bytes."""
    global _used
    pictures = sorted(_all_pictures(), key=lambda path: path.stat().st_mtime)
    total = sum(path.stat().st_size for path in pictures)
    removed = 0
    for path in pictures:
        if total <= target:
            break
        size = path.stat().st_size
        path.unlink(missing_ok=True)
        total -= size
        removed += 1
    with _lock:
        _used = total
    if removed:
        logger.info("Picture cache: removed %d least recently used pictures", removed)
    return removed


def clear() -> int:
    return evict(0)


@dataclass(frozen=True)
class LinkedUse:
    dataset_id: str
    uri: str
    pictures: int
    cached: int


def per_dataset() -> list[LinkedUse]:
    """Each linked dataset's pictures and how many of them are cached."""
    out = []
    for link in all_links():
        if not link.dataset_id:
            continue
        with transaction() as connection:
            rows = connection.execute(
                "SELECT path FROM images WHERE dataset_id = ?", (link.dataset_id,)
            ).fetchall()
        cached = sum(1 for row in rows if Path(row["path"]).is_file())
        out.append(LinkedUse(link.dataset_id, link.uri, len(rows), cached))
    return out


def clean_up_links(settings: Settings | None = None) -> int:
    """Doc 149: links without a dataset (a check never linked, a dataset deleted) go."""
    with transaction(settings) as connection:
        datasets = {row["id"] for row in connection.execute("SELECT id FROM datasets")}
    gone = [link for link in all_links(settings) if link.dataset_id not in datasets]
    for link in gone:
        _remove(link, settings)
    if gone:
        with _lock:
            global _used
            _used = None
        logger.info("Removed %d cloud links without a dataset", len(gone))
    return len(gone)


def _remove(link: Link, settings: Settings | None) -> None:
    shutil.rmtree(link.cache_root, ignore_errors=True)
    delete_link(link.id, settings)


def reset() -> None:
    global _used
    with _lock:
        _used = None
