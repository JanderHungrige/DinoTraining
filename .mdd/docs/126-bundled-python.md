---
id: 126-bundled-python
title: Bundled Runtime — uv, the Backend Source and the Lock in the App; Python and Packages in the User's Data Folder
edition: DinoTraining
depends_on: [125-dependency-lock, 56-sidecar-bundling, 58-installers]
relates: [127-first-run-setup, 129-update-sync, 131-installer-smoke-ci]
source_files:
  - apps/desktop/src-tauri/src/runtime.rs
  - apps/desktop/src-tauri/src/sidecar.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/desktop/src-tauri/tauri.release.conf.json
  - scripts/stage_runtime.py
  - .github/workflows/release.yml
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/runtime.rs (unit tests)
  - scripts/test_stage_runtime.py
data_flow: greenfield
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [installer, uv, python, tauri, sidecar, packaging]
path: Installer/Runtime
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Until doc 127 the first start installs the cpu variant without asking and shows only 'Starting' in the window; uv's progress goes to the log (stdout and ~/Library/Logs/com.dinotraining.app/DinoTraining.log)."
  - "The CUDA panel (GpuPanel, doc 57) still describes the downloaded CUDA sidecar that is now gone; doc 128 replaces it with the variant switch."
security_read_sites: []
sister_projects: []
---

# 126 — Bundled Runtime

## Purpose

- **What goes:** PyInstaller's frozen 636 MB sidecar. It fixed PyTorch at build time, so
  there was no GPU choice, no small installer, and a Windows binary that virus scanners
  like to flag.
- **What the app carries instead:**
  - the **`uv`** binary (pinned, checksum-verified at build);
  - the **backend source** (`app/`, `pyproject.toml`, `uv.lock` from doc 125).
  - Everything else, Python included, is installed on the user's machine from the
    official sources.

## Layout

**In the app bundle** (Tauri resources, read-only):

```
runtime/
  uv            (uv.exe on Windows)
  backend/
    app/  pyproject.toml  uv.lock
```

**In the user's data folder** (writable, no admin rights), next to today's `data/`:
- macOS `~/Library/Application Support/DinoTraining/runtime/`
- Windows `%APPDATA%\DinoTraining\runtime\`
- Linux `~/.local/share/DinoTraining/runtime/`
- or `DINO_RUNTIME_DIR` when set.

```
runtime/
  python/        uv-managed CPython 3.12 (python-build-standalone)
  env/           the virtual environment the backend runs in
  cache/          uv's download cache (what makes a retry resume, doc 127)
  installed.lock  a copy of the lock the environment was synced from
  installed.json  {variant, installed_at (Unix seconds)}
```

## How it runs

- **Every `uv` call is isolated from the user's own setup:**
  - `UV_PYTHON_INSTALL_DIR=runtime/python`, `UV_CACHE_DIR=runtime/cache`,
    `UV_PROJECT_ENVIRONMENT=runtime/env`;
  - `UV_PYTHON_PREFERENCE=only-managed`: never a system Python;
  - `UV_NO_CONFIG=1`: never a user's `uv.toml`.
- **Installing** is `uv sync --frozen --extra <variant> --python 3.12`, run in the bundled
  `backend/`. It fetches CPython from python-build-standalone, and the packages from PyPI
  and download.pytorch.org, exactly as locked.
- **The environment is ready** when `env/`'s Python exists and `installed.lock` is byte for
  byte the bundled `uv.lock` (a copy compares without a hashing crate in the shell). Both
  files are written only after a successful sync, so an interrupted one is never taken
  for finished. Otherwise doc 127's setup runs first. An app update
  with a new lock re-syncs (doc 129).
- **Launching** is the existing `Launch::Module`: `env/…/python -m app`, run in the bundled
  `backend/`.
  - On macOS the launch adds `PYTORCH_ENABLE_MPS_FALLBACK=1`: an operation MPS lacks runs
    on the CPU instead of failing.
- **Development is unchanged:** no bundled runtime means the repository's `backend/.venv`,
  as today.
- **Gone:**
  - `Launch::Frozen`;
  - the downloaded CUDA sidecar (doc 57's `runtimes/cuda`, never built);
  - PyInstaller in the release build (`backend/bundling/` stays in git history only).

## Build

- **`scripts/stage_runtime.py <target-triple>`:**
  - copies the backend source (without tests, caches or `.venv`) into
    `apps/desktop/src-tauri/runtime/`;
  - downloads `uv` for the target from its GitHub release, verified against the release's
    `.sha256`;
  - writes `runtime/VERSION.json` (the uv version, the target, the lock's sha256).
- **`tauri.release.conf.json`** bundles `runtime/` as a resource.
- **`release.yml`:** the PyInstaller step is replaced by the staging step, and the size of
  each installer is recorded in the job summary.

## Verified (2026-09-30)

- **`stage_runtime.py aarch64-apple-darwin`:** 252 backend files, uv 0.12.21 checksum
  verified; `test_stage_runtime.py` (5): only `app/`, `pyproject.toml` and `uv.lock` ship
  (no tests, caches, `.venv` or `.env`), a stale staging is cleared, Windows gets `uv.exe`,
  an unknown target and a wrong checksum stop the build.
- **Rust (3 unit tests):** a checkout has no bundled runtime; ready only with a Python and
  the same lock (a new lock is not ready); uv's environment is isolated from the user's.
- **The release app, built locally** (`tauri build --bundles app`): **46 MB**, against
  298 MB for Wave 8's dmg with the PyInstaller sidecar.
  - First start with an empty `DINO_RUNTIME_DIR`: installed CPython 3.12 (73 MB) and the
    `cpu` environment (869 MB, cache 821 MB) and answered `/health` with `device: mps`
    after **54 s**.
  - Second start: healthy after **5 s**, nothing reinstalled.
  - `/api/v1/datasets` and `/api/v1/models` answered from the isolated data folder.
- **Found on the way:** every log line was written twice (the log plugin's defaults
  already include stdout); the extra target is gone, and the log folder target now
  keeps a file a user can send.
- **CI (`lock-check.yml`, run 36769664018):** the install from the lock succeeded on all
  three runners; three tests had never run off this Mac and failed there — a POSIX file
  mode on Windows, the MPS test on a runner whose MPS has no memory, and the unfreeze tests
  needing downloaded weights. They now skip on such machines; the whole suite with empty
  model caches: 1877 passed, 17 skipped.
