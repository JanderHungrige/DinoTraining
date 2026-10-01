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
from pathlib import Path

from PIL import Image

from app.cloud.links import find, storage_for

logger = logging.getLogger(__name__)

HEADER_BYTES = 64 * 1024

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


def ensure_local(path: Path) -> Path:
    """The picture as a local file, downloaded into the link's cache if it is not there."""
    if path.is_file():
        return path
    found = find(path)
    if found is None:
        return path  # an ordinary missing file: the caller reports it as before
    link, key = found
    data = storage_for(link).get(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as file:
            file.write(data)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    logger.debug("Fetched %s from %s", key, link.bucket)
    return path
