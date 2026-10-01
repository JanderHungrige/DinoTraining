"""Standard streams for a backend started without any (the Windows app, doc 139).

A GUI program on Windows has no console, and a process it starts inherits no standard
handles: Python then sets ``sys.stdout`` and ``sys.stderr`` to ``None``. uvicorn's
logging setup calls ``sys.stdout.isatty()`` and the backend died with "Unable to
configure formatter 'default'" (exit code 1), its traceback written nowhere. Found on
Jan's Windows PC; CI never saw it, because the smoke test starts the app with its output
redirected.
"""

from __future__ import annotations

import os
import sys


def ensure_streams() -> list[str]:
    """Give a missing stdout or stderr somewhere to write. Returns the names it replaced."""
    replaced: list[str] = []
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            # Line-buffered text, like the real streams; the shell collects nothing here,
            # but nothing that writes or asks isatty() can fail any more.
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8", buffering=1))  # noqa: SIM115
            replaced.append(name)
    return replaced
