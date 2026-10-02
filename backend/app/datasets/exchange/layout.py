"""Where an export's files go, and how picture paths travel (doc 142).

An export is a folder `v-rex/` inside its target: `v-rex.json` (the whole dataset),
`annotations.coco.json` (for other tools) and, optionally, `pictures/`.
Picture paths inside are relative to the pictures' folder: the common parent of every
picture, so a moved folder or another machine still matches.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path, PurePosixPath

EXPORT_DIR = "v-rex"
DATA_FILE = "v-rex.json"
COCO_FILE = "annotations.coco.json"
PICTURES_DIR = "pictures"
FORMAT = "v-rex-export"
FORMAT_VERSION = 1

# Doc 159: exports written before the rename to V-Rex are read as they are; new ones are
# written under the new name only.
LEGACY_EXPORT_DIR = "dinotraining"
LEGACY_DATA_FILE = "dinotraining.json"
LEGACY_FORMAT = "dinotraining-export"
EXPORT_DIRS = frozenset({EXPORT_DIR, LEGACY_EXPORT_DIR})
FORMATS = frozenset({FORMAT, LEGACY_FORMAT})


def pictures_root(paths: list[str]) -> Path | None:
    """The folder every picture lies under; None for a dataset without pictures."""
    if not paths:
        return None
    parents = [str(Path(path).parent) for path in paths]
    try:
        return Path(os.path.commonpath(parents))
    except ValueError:
        # Windows: pictures on two drives share no folder. Their paths stay absolute.
        return None


def relative(path: str, root: Path) -> str:
    """A picture's path as stored in an export: forward slashes, relative to `root`."""
    return Path(path).relative_to(root).as_posix()


def resolve(relative_path: str, root: Path) -> Path:
    """A stored path back to a file under `root`; ValueError if it would leave it."""
    parts = PurePosixPath(relative_path)
    if parts.is_absolute() or ".." in parts.parts:
        raise ValueError(f"The export names a picture outside its folder: {relative_path!r}.")
    return root.joinpath(*parts.parts)


def export_folder(target: Path) -> Path:
    return target / EXPORT_DIR


def find_export(path: Path) -> Path | None:
    """The export's `v-rex.json` in a folder or its `v-rex/`, or one from before the rename."""
    for candidate in (
        path / EXPORT_DIR / DATA_FILE,
        path / DATA_FILE,
        path / LEGACY_EXPORT_DIR / LEGACY_DATA_FILE,
        path / LEGACY_DATA_FILE,
    ):
        if candidate.is_file():
            return candidate
    return None


def write_atomically(path: Path, text: str) -> None:
    """Write beside, then rename over: an interrupted export keeps the previous file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
