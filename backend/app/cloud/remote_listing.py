"""A bucket's listing as doc 136's `Listing` (doc 148): annotation files downloaded into the
link's cache, pictures only named, at their future cache paths."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePosixPath

from app.cloud.links import Link, cache_path, storage_for
from app.cloud.pictures import remember_listing
from app.datasets.intake.walk import MAX_FILES, Listing, TooLargeError, sort_into

logger = logging.getLogger(__name__)

ANNOTATION_SUFFIXES = frozenset({".json", ".txt", ".xml", ".yaml", ".yml"})
PARALLEL = 16

Progress = Callable[[int, int, str], None]


def remote_listing(link: Link, progress: Progress = lambda _done, _total, _what: None) -> Listing:
    """List the bucket under the link's prefix; fetch only what annotations are made of."""
    storage = storage_for(link)
    listing = Listing(root=link.cache_root)
    keys: set[str] = set()
    to_fetch: list[str] = []
    for page in storage.list():
        for entry in page:
            if len(keys) >= MAX_FILES:
                raise TooLargeError(
                    f"{storage.where} holds more than {MAX_FILES:,} files: "
                    "link the dataset's own prefix"
                )
            path = cache_path(link, entry.key)
            keys.add(entry.key)
            sort_into(listing, path)
            if PurePosixPath(entry.key).suffix.lower() in ANNOTATION_SUFFIXES:
                to_fetch.append(entry.key)
        progress(len(keys), 0, "listing")
    remember_listing(link.id, keys)
    _fetch(link, to_fetch, progress)
    return listing


def _fetch(link: Link, keys: list[str], progress: Progress) -> None:
    storage = storage_for(link)

    def one(key: str) -> None:
        target = cache_path(link, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(storage.get(key))

    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        for done, _ in enumerate(pool.map(one, keys), start=1):
            if done % 50 == 0 or done == len(keys):
                progress(done, len(keys), "annotation files")
    logger.info("Linked %s: %d annotation files fetched", storage.where, len(keys))
