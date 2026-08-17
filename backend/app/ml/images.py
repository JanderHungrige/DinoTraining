"""Reading the user's image files.

These are the only reads in the app that touch paths outside its own directories —
the user picks a folder, so confinement is not the applicable control. Instead every
read is narrowed to "a file PIL can open as one of a small set of formats", which
turns "read any file" into "confirm a file is a valid image".
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

# Formats PIL reports after a successful open. Extensions are a hint; this is the check.
ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "BMP", "WEBP", "TIFF", "GIF"})

IMAGE_SUFFIXES = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".gif"}
)


class ImageReadError(ValueError):
    """The path is not a readable image."""


class FolderNotFoundError(FileNotFoundError):
    """The folder does not exist or is not a directory."""


def _looks_like_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def read_image(path_str: str) -> tuple[Image.Image, Path]:
    """Open an image as RGB. Raises ImageReadError for anything that is not one."""
    path = Path(path_str).expanduser()

    if not path.is_file():
        raise FileNotFoundError(f"No such image: {path_str}")

    try:
        with Image.open(path) as opened:
            image_format = opened.format
            if image_format not in ALLOWED_FORMATS:
                raise ImageReadError(f"Unsupported image format: {image_format}")
            # load() before the context closes; convert detaches from the file handle.
            return opened.convert("RGB"), path
    except UnidentifiedImageError as error:
        raise ImageReadError(f"Not a readable image: {path.name}") from error
    except OSError as error:
        # Truncated or permission-denied files land here. Report as a bad image
        # rather than a 500 — a corrupt file in a photo folder is expected input.
        logger.info("Could not read image %s: %s", path.name, error)
        raise ImageReadError(f"Could not read image: {path.name}") from error


def list_images(folder_str: str) -> list[Path]:
    """Image files directly inside a folder, sorted. Non-recursive by design.

    Non-recursive so pointing this at ``/`` enumerates one level instead of walking
    the user's entire disk.
    """
    folder = Path(folder_str).expanduser()
    if not folder.is_dir():
        raise FolderNotFoundError(f"Not a folder: {folder_str}")

    return sorted(
        entry
        for entry in folder.iterdir()
        if entry.is_file() and not entry.name.startswith(".") and _looks_like_image(entry)
    )
