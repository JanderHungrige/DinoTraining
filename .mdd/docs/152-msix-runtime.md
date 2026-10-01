---
id: 152-msix-runtime
title: MSIX Runtime — The App Under Package Identity, Measured; the Store Edition Writes to Its Package Folder by Its Real Path
edition: DinoTraining
depends_on: [151-msix-package, 126-bundled-python, 141-vc-runtime]
relates: [153-msix-smoke-ci, 156-store-aware-app]
source_files:
  - apps/desktop/src-tauri/src/support_dir.rs
  - apps/desktop/src-tauri/src/sidecar.rs
  - backend/app/core/paths.py
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/support_dir.rs
  - backend/tests/test_paths.py
data_flow: writes-existing
last_synced: 2026-10-02
status: in_progress
phase: all
mdd_version: 11
tags: [msix, microsoft-store, appdata-redirection, uv, runtime, windows]
path: Installer/Windows/MSIX/Runtime
initiative: dinotraining
wave: dinotraining-wave-15-10
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The Tauri log folder (%LOCALAPPDATA%\\com.dinotraining.app\\logs) is still written through the redirection: on a PC that also has the EXE edition, both editions append to the same log."
security_read_sites: []
sister_projects: []
---

# 152 — MSIX Runtime

## Purpose

- **Does the app work under package identity?** Measured, not assumed: on the release
  workflow's Windows runner (doc 153) first, then on Jan's PCs.

## Measured on the runner (2026-10-01, release dry runs)

| Run | What happened | Finding |
|---|---|---|
| 36926429104 | healthy after 58 s, runtime in the **real** `%LOCALAPPDATA%\DinoTraining` | The EXE smoke test had left that folder, and the test's own `setup-auto` file created it. **Windows does not redirect into an `AppData` folder that already exists:** the Store edition shared the EXE's runtime and data, and an uninstall would not have removed them. |
| 36928735299 | clean `AppData`: setup starts, Python downloads, then **uv fails**: "Missing expected target directory for Python minor version link at …\AppData\Local\DinoTraining\runtime\python\cpython-3.12.14-windows-x86_64-none" | **R5 answered:** uv links the minor version (`cpython-3.12-…` → `cpython-3.12.14-…`) with a junction. Through the redirection, the junction's target is the unredirected path, which does not exist. |

## The decision: the Store edition writes to its package folder directly

- **The shell's folder** (`support_dir::app_support_root`) is, under package identity,
  `%LOCALAPPDATA%\Packages\<family>\LocalCache\Local\DinoTraining`: the place the
  redirection would have used, written by its **real path**.
  - **uv's junctions** point to real paths;
  - **every process** (Explorer, uv, python, Notepad) sees the same files under the same
    name;
  - **Windows still removes the folder** with the package (it is the package's own);
  - **a folder the EXE edition left is ignored:** the editions do not share runtime or
    data. Moving work between them is the dataset export and restore (doc 142).
- **The backend is told** (`DINO_APP_DIR`, set by the sidecar only under package
  identity): its `default_data_dir()` honours it, so data, models, the database and the
  cloud cache sit beside the runtime. Outside the Store nothing changes.

## Still to measure (next dry run, then Jan's PCs)

- **The first-run setup end to end** in the package folder, PyTorch importing there, a
  second start, removal (doc 153 asserts all of it).
- **R1, WebView2:** present on the runner (Windows Server 2025) and on Windows 11; Windows
  10 without it is untested.
- **R2/R3, the Visual C++ runtime:** the runner's is current, so doc 141's installer did
  not run. Whether the framework dependency `Microsoft.VCLibs.140.00.UWPDesktop` reaches
  `python.exe` (R2) and whether certification accepts doc 141's installer (R3) is open;
  doc 141's installer stays meanwhile.
- **On Jan's PCs:** the CPU⇄GPU switch (doc 128), an update with a new lock (doc 129),
  "Open the log", exports and "Show in Explorer", the cloud cache.

## Tests

- **Rust:** the Store edition's folder is the package's `LocalCache\Local\DinoTraining`;
  outside the Store the backend is not given a folder.
- **Backend:** `DINO_APP_DIR` names the app folder; empty or blank is ignored.
