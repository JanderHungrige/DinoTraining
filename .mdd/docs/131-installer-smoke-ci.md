---
id: 131-installer-smoke-ci
title: Installer Smoke Test — Install, First Start, Health, a Torch Check and a Second Start on All Three Platforms
edition: DinoTraining
depends_on: [126-bundled-python, 127-first-run-setup, 130-mac-distribution]
relates: [58-installers, 125-dependency-lock]
source_files:
  - .github/workflows/release.yml
  - scripts/smoke_installed.py
routes: []
models: []
test_files:
  - scripts/test_smoke_installed.py
data_flow: greenfield
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [installer, ci, smoke-test, release, windows, linux, macos]
path: Installer/SmokeCI
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 131 — Installer Smoke Test

## Purpose

- **Wave 8's installers were built, never started.** Windows was never run at all.
- **Now every release build proves, on each platform, that what a user downloads
  works:**
  - it installs;
  - its first start installs Python and PyTorch;
  - the backend answers;
  - PyTorch runs;
  - a second start needs no setup.

## Per platform (in the release workflow, after the build)

| | Install | Start | Remove |
|---|---|---|---|
| Windows | NSIS installer with `/S` (per user, no admin) | the installed `.exe` | its `uninstall.exe /S` |
| Linux | `apt-get install ./….deb` | the installed binary under `xvfb-run` (a virtual display for the webview) | `apt-get remove` |
| macOS | `scripts/install-mac.sh` with the built archive (doc 130's real path) | the app in `~/Applications` | the folder |

## The check — `scripts/smoke_installed.py <executable>`

1. **First start, unattended:** `DINO_SETUP_AUTO=cpu` (doc 127), with runtime and data
   folders in the job's temporary folder. It waits for `/api/v1/health`, for up to 25
   minutes: the runners download about 1 GB.
2. **The environment:** `runtime/current` names an environment with a Python
   (doc 129). That Python imports torch, torchvision and onnxruntime, and multiplies two
   tensors.
3. **Second start** without `DINO_SETUP_AUTO`: healthy within 3 minutes, and nothing
   reinstalled (`current` unchanged).
4. **Stops the app and its backend:** `taskkill /T` on Windows; SIGTERM elsewhere, which
   the shell passes on to the backend.
5. **The job summary** records the first-start time, the second-start time and the sizes
   of the installed environment and uv's cache, next to the installer size (doc 126).
6. **On failure** it prints the app's log tail and exits non-zero. The app log is kept
   as an artifact.

- **Not a model inference:** that would download weights from Hugging Face in every
  release build. The torch check proves the installed PyTorch runs; the models' own
  paths are the backend suite's job (doc 125's lock check runs it on all three
  platforms).
- **CPU only:** the runners have no GPU. The CUDA variants are checked in the lock
  (doc 125) and switched in the app (doc 128).
