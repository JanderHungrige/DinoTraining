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

import shutil
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

#: Where the flattened third-party licence texts end up.
LICENCE_ROLLUP = "THIRD_PARTY_LICENCES.txt"

#: Longest path, relative to the frozen output's root, that the Windows bundler survives.
#:
#: `makensis` fails at the 260-character MAX_PATH and **is not long-path aware** — it is a
#: legacy Win32 binary without the manifest that opts in, so `LongPathsEnabled` in the
#: registry does nothing for it. On a GitHub runner the base is already 84 characters
#: (`D:\a\repo\repo\apps\desktop\src-tauri\binaries\dinotraining-sidecar\`), which
#: leaves 176. 140 keeps room for a deeper checkout without another failed release.
MAX_RELATIVE_PATH = 140


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
    code = subprocess.run(command, cwd=BACKEND).returncode
    if code != 0:
        return code

    output = BACKEND / "dist" / NAME
    kept, removed = flatten_licences(output)
    print(f"licences: {kept} text(s) rolled up, {removed} deep tree(s) removed", flush=True)

    too_long = overlong_paths(output)
    if too_long:
        print(
            f"{len(too_long)} path(s) exceed {MAX_RELATIVE_PATH} characters and would "
            f"break the Windows bundler:",
            file=sys.stderr,
        )
        for path in too_long[:10]:
            print(f"  {len(path)} {path}", file=sys.stderr)
        return 1

    print(f"longest relative path: {max(len(p) for p in relative_paths(output))}", flush=True)
    return 0


def relative_paths(root: Path) -> list[str]:
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]


def overlong_paths(root: Path) -> list[str]:
    return sorted((p for p in relative_paths(root) if len(p) > MAX_RELATIVE_PATH), key=len)


def flatten_licences(root: Path) -> tuple[int, int]:
    """Collect vendored licence texts into one file, then remove the deep trees.

    **This is a compliance requirement, not tidying.** torch vendors the licences of its own
    dependencies at paths like

        torch-2.13.0+cpu.dist-info/licenses/third_party/kineto/libkineto/third_party/
        dynolog/third_party/prometheus-cpp/3rdparty/civetweb/src/third_party/
        duktape-1.5.2/LICENSE.txt

    which is 181 characters on its own and pushed the absolute path to 265 — five over
    MAX_PATH — killing the Windows build. Deleting them would fix that and would also drop
    licence texts that BSD and MIT **require** to be reproduced in a distribution. So they
    are concatenated into one file, each under a header naming where it came from, and only
    then are the trees removed.

    Nothing reads these at runtime: `importlib.metadata` uses `METADATA` and `RECORD`, both
    of which stay.
    """
    trees = [d for d in root.rglob("*.dist-info/licenses") if d.is_dir()]
    if not trees:
        return 0, 0

    sections: list[str] = [
        "Third-party licence texts bundled with the DinoTraining sidecar.",
        "",
        "Flattened from their original locations so that Windows' 260-character path",
        "limit does not break packaging. The texts are unmodified; only their paths are.",
        "",
    ]
    kept = 0
    for tree in sorted(trees):
        for licence in sorted(tree.rglob("*")):
            if not licence.is_file():
                continue
            sections.append("=" * 78)
            sections.append(str(licence.relative_to(root)))
            sections.append("=" * 78)
            sections.append(licence.read_text(encoding="utf-8", errors="replace"))
            sections.append("")
            kept += 1

    (root / "_internal" / LICENCE_ROLLUP).write_text("\n".join(sections), encoding="utf-8")
    for tree in trees:
        shutil.rmtree(tree)
    return kept, len(trees)


if __name__ == "__main__":
    raise SystemExit(main())
