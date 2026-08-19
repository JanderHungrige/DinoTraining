"""Filesystem locations and the confinement check that guards them.

Every path derived from external input passes through :func:`ensure_within`. Model
directories are produced by :func:`resolve_model_dir` and nowhere else — building a
cache path by hand is how a `../` eventually reaches somewhere it should not.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app.core.config import Settings, get_settings

APP_DIR_NAME = "DinoTraining"


class PathConfinementError(ValueError):
    """Raised when a resolved path escapes the directory it must stay inside."""


def default_data_dir() -> Path:
    """Per-user application data directory, by platform convention."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_DIR_NAME
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / APP_DIR_NAME


def model_cache_root(settings: Settings | None = None) -> Path:
    """Where model weights are cached. Honours DINO_MODEL_CACHE_DIR when set."""
    settings = settings or get_settings()
    if settings.model_cache_dir is not None:
        return settings.model_cache_dir.expanduser().resolve()
    return (default_data_dir() / "models").resolve()


def ensure_within(root: Path, candidate: Path) -> Path:
    """Return ``candidate`` resolved, or raise if it is not inside ``root``.

    Resolution happens first so symlinks and ``..`` segments are collapsed before the
    comparison — checking the unresolved string is the classic way to get this wrong.
    """
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise PathConfinementError(f"Path escapes {resolved_root}")
    return resolved


def resolve_model_dir(model_id: str, settings: Settings | None = None) -> Path:
    """Cache directory for one model. The only sanctioned way to build this path.

    ``model_id`` must already be a known registry key; this still confines the result
    so a future caller that forgets the lookup cannot traverse out.
    """
    root = model_cache_root(settings)
    return ensure_within(root, root / model_id)


def directory_size_bytes(path: Path) -> int:
    """Total size of a directory tree. Missing directories count as zero."""
    if not path.is_dir():
        return 0
    total = 0
    for entry in path.rglob("*"):
        # Symlinks are not followed: an HF cache is full of them, and following would
        # double-count blobs or wander outside the tree entirely.
        if entry.is_file() and not entry.is_symlink():
            total += entry.stat().st_size
    return total


# What an actual set of model weights looks like on disk.
WEIGHT_SUFFIXES = frozenset({".safetensors", ".bin", ".pth", ".pt", ".onnx", ".msgpack"})


def is_installed(path: Path) -> bool:
    """A model counts as installed only once its *weights* are on disk.

    Checking for a merely non-empty directory reports success the moment
    ``snapshot_download`` writes ``config.json`` — while several hundred MB of
    weights are still in flight. That made the catalogue show "Installed" mid
    download, 409 a retry, and hand the loader a half-written model.
    """
    if not path.is_dir():
        return False
    return any(
        entry.is_file() and entry.suffix.lower() in WEIGHT_SUFFIXES for entry in path.iterdir()
    )


def free_disk_bytes(path: Path) -> int:
    """Free space on the volume holding ``path``, walking up to an existing parent."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    usage = os.statvfs(probe) if hasattr(os, "statvfs") else None
    if usage is None:  # pragma: no cover - Windows path, exercised in Wave 8
        import shutil

        return shutil.disk_usage(probe).free
    return usage.f_bavail * usage.f_frsize
