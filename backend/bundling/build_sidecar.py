#!/usr/bin/env python3
"""Freeze the FastAPI + PyTorch sidecar into a Tauri external binary (doc 56).

Run from `backend/`, inside an environment holding the **production** dependencies plus
PyInstaller — not the development venv, whose mypy, ruff and pytest would be frozen in
alongside the app for no reason:

    python -m venv .build && .build/bin/pip install . pyinstaller
    .build/bin/python bundling/build_sidecar.py

Produces `dist/dinotraining-sidecar/` — a directory, because PyInstaller's `--onedir`
output is an executable plus `_internal/` holding 568 MB of torch.

**The name carries no target triple**, deliberately. An earlier version added one because
Tauri's `externalBin` requires it, but `externalBin` takes a single *file* and this is a
directory, so the sidecar ships as a Tauri **resource** instead. Nothing at runtime then
needs to know the triple, and the Rust side can look for one fixed name on every platform.
The triple is printed for the release job to label its artefact with.

**Per platform.** PyInstaller does not cross-compile and the torch wheel differs by
platform, so this runs on each of macOS, Windows and Linux. That is why Wave 8's release
job is a build matrix rather than one runner — see doc 56 for the size consequences, which
are large enough to be a product decision rather than a build detail.

**This directory is not called `packaging`.** It was, for about an hour, and that put
`backend/packaging/` on `sys.path` ahead of the real `packaging` PyPI package — which
setuptools, transformers and huggingface-hub all import. `pip install .` failed outright;
the frozen build would have failed later and more mysteriously.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

NAME = "dinotraining-sidecar"
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent

#: Imports PyInstaller's static analysis cannot see. uvicorn selects its loop, protocol and
#: lifespan implementations by *string* at runtime, so nothing references them statically —
#: the frozen build starts, and then fails on the first request with an import error.
HIDDEN = (
    "uvicorn.logging",
    "uvicorn.loops.uvloop",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
)

#: `transformers` resolves model classes through a lazy registry keyed by config strings, so
#: no import statement anywhere mentions `RfDetrForObjectDetection` or `Dinov2Model`.
#: Collecting the package wholesale is heavy-handed and is the only thing that works.
COLLECT = ("app", "transformers")


def target_triple() -> str:
    """The host triple, read from the Rust toolchain itself — for the *artefact label*.

    Asked rather than guessed: `aarch64-apple-darwin` and `x86_64-apple-darwin` are both
    plausible on the same machine depending on the toolchain, and a release labelled with
    the wrong one is downloaded by users it cannot run on.
    """
    result = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True)
    for line in result.stdout.splitlines():
        if line.startswith("host:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit("could not read the host triple from `rustc -vV`")


def main() -> int:
    print(f"host triple: {target_triple()}", flush=True)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        NAME,
        # `onedir`, not `onefile`: a onefile build unpacks ~600 MB to a temp directory on
        # every launch, which is seconds of disk churn before the port binds — and the app
        # looks hung for exactly as long.
        "--onedir",
        "--noconfirm",
        "--clean",
        "--paths",
        str(BACKEND),
        *[arg for name in COLLECT for arg in ("--collect-all", name)],
        "--collect-submodules",
        "uvicorn",
        *[arg for name in HIDDEN for arg in ("--hidden-import", name)],
        str(HERE / "entry.py"),
    ]
    print(" ".join(command), flush=True)
    return subprocess.run(command, cwd=BACKEND).returncode


if __name__ == "__main__":
    raise SystemExit(main())
