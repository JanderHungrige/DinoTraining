---
id: 153-msix-smoke-ci
title: MSIX Smoke Test — The Store Edition Installed, Started Through Its Package Identity, Set Up and Removed in CI
edition: DinoTraining
depends_on: [151-msix-package, 131-installer-smoke-ci]
relates: [152-msix-runtime]
source_files:
  - scripts/smoke_msix.ps1
  - apps/desktop/src-tauri/src/setup_flow.rs
  - .github/workflows/release.yml
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/setup_flow.rs
data_flow: greenfield
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [msix, microsoft-store, smoke-test, ci, windows, package-identity]
path: Installer/Windows/MSIX/Smoke
initiative: dinotraining
wave: dinotraining-wave-15-10
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 153 — MSIX Smoke Test

## Purpose

- **Doc 131 installs and starts the EXE in CI. This does the same for the Store
  edition,** the way a user starts it.
- **Started through its package identity** (`shell:AppsFolder\<family>!DinoTraining`),
  not by running the exe:
  - it inherits **no standard handles**, the gap doc 139 found in doc 131's test;
  - it inherits **no environment**;
  - its `AppData` writes are **redirected**, as on a user's PC.

## The run (`scripts/smoke_msix.ps1`, in the release workflow after the EXE's)

0. **A clean `AppData`:** an existing `%LOCALAPPDATA%\DinoTraining` (doc 131's EXE run
   leaves one on the runner) is moved aside and put back at the end.
   - **Why:** Windows writes into an `AppData` folder that already exists instead of
     redirecting it. The first run of this test, with that folder present, set up nothing
     (healthy after 58 s) and reused the EXE's runtime in the real folder.
1. **Trust** doc 151's test certificate (`LocalMachine\TrustedPeople`) and
   `Add-AppxPackage` the test-signed MSIX.
2. **Write `setup-auto` = `cpu`** into the package's redirected folder
   (`%LOCALAPPDATA%\Packages\<family>\LocalCache\Local\DinoTraining`).
   - A packaged start inherits no `DINO_SETUP_AUTO`, so the app also reads it from this
     file (`setup_flow.rs`), under its usual path.
   - Written into the real folder instead, it would create that folder and switch the
     redirection off (step 0).
3. **Start it** through its identity; wait for `/health` (first start: Python and PyTorch
   download, up to 25 min).
4. **The runtime must be in the redirected folder,** PyTorch must import there, and the
   real `%LOCALAPPDATA%\DinoTraining` must not exist. The job summary gives its size.
5. **Stop it, start it again:** `/health` without setup.
6. **`Remove-AppxPackage`,** and check that Windows removed the package's data folder with
   it: what the uninstall notice (doc 146) promises.
- **On failure, the app's logs from the redirected folder are kept** as an artifact.
