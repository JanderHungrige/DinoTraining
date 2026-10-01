"""Walking a dataset folder without walking the user's disk (doc 136).

Bounded in depth and in count: a dataset is a few levels deep (``train/images/x.jpg``,
``Annotations/x.xml``, OSDaR23's ``<sequence>/rgb_center/x.png``), and a path pointed at
``/`` by mistake must end in a refusal, not an hour of scanning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.ml.images import IMAGE_SUFFIXES
from app.ml.video.decode import VIDEO_SUFFIXES

MAX_DEPTH = 5
MAX_FILES = 300_000
#: Folders a dataset never needs and that are large or private.
SKIPPED = {".git", "__pycache__", "node_modules", ".venv", "venv", ".cache"}


class TooLargeError(ValueError):
    """More files than any dataset folder should hold: probably not a dataset folder."""


@dataclass
class Listing:
    root: Path
    pictures: list[Path] = field(default_factory=list)
    videos: list[Path] = field(default_factory=list)
    json_files: list[Path] = field(default_factory=list)
    txt_files: list[Path] = field(default_factory=list)
    xml_files: list[Path] = field(default_factory=list)
    yaml_files: list[Path] = field(default_factory=list)


def walk(root: Path) -> Listing:
    """Every file of interest under ``root``, sorted, at most MAX_DEPTH levels down."""
    if not root.is_dir():
        raise ValueError(f"Not a folder: {root}")
    listing = Listing(root=root)
    seen = 0
    base_depth = len(root.parts)
    for directory, subdirs, files in os.walk(root):
        depth = len(Path(directory).parts) - base_depth
        subdirs[:] = sorted(d for d in subdirs if d not in SKIPPED and not d.startswith("."))
        if depth >= MAX_DEPTH:
            subdirs[:] = []
        for name in sorted(files):
            seen += 1
            if seen > MAX_FILES:
                raise TooLargeError(
                    f"{root} holds more than {MAX_FILES:,} files within {MAX_DEPTH} levels: "
                    "choose the dataset's own folder"
                )
            sort_into(listing, Path(directory) / name)
    return listing


def sort_into(listing: Listing, path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        listing.pictures.append(path)
    elif suffix in VIDEO_SUFFIXES:
        listing.videos.append(path)
    elif suffix == ".json":
        listing.json_files.append(path)
    elif suffix == ".txt":
        listing.txt_files.append(path)
    elif suffix == ".xml":
        listing.xml_files.append(path)
    elif suffix in {".yaml", ".yml"}:
        listing.yaml_files.append(path)
