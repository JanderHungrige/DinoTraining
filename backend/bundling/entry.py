"""Frozen entry point for the sidecar (doc 56).

The **only** file the packaged build needs that the development path does not. PyInstaller
freezes a script rather than a module, so `python -m app` has no equivalent; everything
this does is what `app/__main__.py` does.

Kept in `packaging/` rather than beside `app/` so it is obvious that nothing imports it at
runtime — it is a build artefact's starting point, not part of the application.
"""

from __future__ import annotations

import multiprocessing
import sys


def run() -> int:
    # Without this a frozen binary re-executes *itself* for every spawned worker on macOS
    # and Windows: the process forks until something gives up, and the port never binds.
    # It costs nothing on Linux and must not be made conditional.
    multiprocessing.freeze_support()

    from app.main import main

    main()
    return 0


if __name__ == "__main__":
    sys.exit(run())
