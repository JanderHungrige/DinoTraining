---
id: 132-uninstall
title: Uninstall — Windows Removes Python and PyTorch, and the Data on Request; Runtime Beside the Data
edition: DinoTraining
depends_on: [126-bundled-python, 131-installer-smoke-ci, 58-installers]
relates: [130-mac-distribution]
source_files:
  - apps/desktop/src-tauri/windows/hooks.nsh
  - apps/desktop/src-tauri/tauri.conf.json
  - apps/desktop/src-tauri/src/runtime.rs
  - scripts/smoke_installed.py
  - .github/workflows/release.yml
  - README.md
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/runtime.rs (unit tests)
  - scripts/test_smoke_installed.py
  - .github/workflows/release.yml (the Windows smoke step checks the uninstall)
data_flow: writes-existing
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [installer, uninstall, windows, nsis, appdata, linux, macos]
path: Installer/Uninstall
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 132 — Uninstall

## Purpose

- **Jan asked (2026-10-01): "Windows needs an uninstall option. Is it in the installer?"**
  - **It is:** Tauri's NSIS installer registers the app under *Settings → Apps* and
    writes `uninstall.exe`.
  - **It did not reach what the app downloads.** Doc 131's smoke test ran it.
- **What it removed:** only its own files, by name, then `RMDir` without `/r`. Its
  "Delete the application data" checkbox removes `%APPDATA%\com.dinotraining.app` and
  `%LOCALAPPDATA%\com.dinotraining.app`, the bundle identifier's folders.
- **What stayed:**
  - Python and PyTorch, 1 to 6 GB, in `%APPDATA%\DinoTraining\runtime`. That is the
    *roaming* profile, which a company network copies at every logon: the wrong place
    for gigabytes.
  - Datasets, trained models and downloaded weights in `%LOCALAPPDATA%\DinoTraining`
    (the backend's folder, doc 03). The app is installed into the same folder.
    Keeping them by default is right; the checkbox should be able to remove them.

## The runtime moves beside the data

- **Windows:** `%LOCALAPPDATA%\DinoTraining\runtime`, beside `data/` and `models/`, and
  no longer roaming. The backend already used `LOCALAPPDATA`; the shell now agrees.
- **Linux:** `$XDG_DATA_HOME/DinoTraining/runtime` when it is set, as the backend does
  (before: always `~/.local/share`).
- **macOS:** unchanged (`~/Library/Application Support/DinoTraining/runtime`).

## The Windows uninstaller (NSIS hook `windows/hooks.nsh`)

After Tauri's own steps, unless the uninstaller runs for an update:

1. **Always** removes `%LOCALAPPDATA%\DinoTraining\runtime`: Python, PyTorch and uv's
   cache, which the app installed and can install again. It also removes the old
   roaming location `%APPDATA%\DinoTraining\runtime`, which builds before this doc
   used.
2. **With "Delete the application data" ticked**, also removes
   `%LOCALAPPDATA%\DinoTraining`: datasets, trained models, downloaded weights,
   settings.
3. Removes the folders if they are empty.

- **The default keeps the user's work.** A silent uninstall (`/S`) leaves the checkbox
  unticked.

## macOS and Linux

They have no uninstaller of their own: a Mac app is a folder, and a `.deb`'s removal
script runs as root and must not touch home folders. The README says what to delete:

- **macOS:** the app, plus `~/Library/Application Support/DinoTraining` for everything
  else. `brew uninstall dinotraining` removes the Homebrew copy.
- **Linux:** `sudo apt remove dino-training`, plus `~/.local/share/DinoTraining`.

## Checked

- **Rust:** the runtime root per platform, from the environment variables (a pure
  function, tested for each OS's inputs).
- **CI (doc 131's Windows step):**
  - the smoke test uses the default runtime location, not an override;
  - after the silent uninstall, the runtime folder and the installed `.exe` are gone,
    the data folder is kept, and the entry under *Apps* is gone.
