"""Entrypoint for ``python -m app``."""

from __future__ import annotations

# Before anything else is imported: a process started without standard streams has
# sys.stdout = None, and logging setup at import or in uvicorn fails on it (doc 139).
from app.core.streams import ensure_streams

ensure_streams()

from app.main import main  # noqa: E402

if __name__ == "__main__":
    main()
