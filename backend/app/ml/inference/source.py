"""What the user pointed the viewer at: one image, or a folder of them.

The deliverable here is the *contract*, not the listing. A single file and a folder come
back as the same shape — a sequence of items under a stable identity — so the viewer has
one thing to consume and the deferred video source has one thing to satisfy.

Both branches go through ``app.ml.images``, which owns the "a file PIL opens as one of a
small set of formats" narrowing. There is deliberately no second file-reading path.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.ml.images import list_images, read_image

SourceKind = Literal["file", "folder"]

# A silent cap is worse than no cap: the user must be able to tell "this folder has 1000
# images" from "you are seeing the first 1000 of 5000". Hence the `truncated` flag.
MAX_ITEMS = 1000


@dataclass(frozen=True, slots=True)
class InputItem:
    """One image the user can select.

    ``item_id`` is not the path, and the reason is not uniqueness — the path is already
    unique. It is that a stable, *path-free* identity is the only part of this contract a
    future video source can also produce. Anything keyed on it (React list keys, a result
    map, feature 18's feature cache) keeps working when items stop being files.
    """

    item_id: str
    name: str
    path: Path


@dataclass(frozen=True, slots=True)
class InputSource:
    kind: SourceKind
    root: Path
    items: tuple[InputItem, ...]
    truncated: bool


def _identity(resolved: Path) -> str:
    return hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:16]


def _item(path: Path) -> InputItem:
    # Resolve first so the same file reached two ways gets one id.
    resolved = path.resolve()
    return InputItem(item_id=_identity(resolved), name=resolved.name, path=resolved)


def resolve_source(path_str: str) -> InputSource:
    """Resolve a user-supplied path into a sequence of images.

    Raises ``FolderNotFoundError``/``FileNotFoundError`` when nothing is there, and
    ``ImageReadError`` when a single file is not a readable image.
    """
    path = Path(path_str).expanduser()

    if path.is_dir():
        found = list_images(str(path))
        return InputSource(
            kind="folder",
            root=path.resolve(),
            # Entries are *not* opened here. Suffix filtering is what `list_images` does,
            # and pre-validating thousands of files would put seconds behind picking a
            # folder while still being stale by the time the user selected one. A corrupt
            # file therefore fails on selection, where the user can act on it.
            items=tuple(_item(entry) for entry in found[:MAX_ITEMS]),
            truncated=len(found) > MAX_ITEMS,
        )

    # A single file is validated by opening it: the extension is a hint, never the check.
    # One decode is affordable for one file; per-entry it would not be.
    read_image(path_str)
    return InputSource(kind="file", root=path.resolve(), items=(_item(path),), truncated=False)
