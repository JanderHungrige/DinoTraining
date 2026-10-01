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

1. **Trust** doc 151's test certificate (`LocalMachine\TrustedPeople`) and
   `Add-AppxPackage` the test-signed MSIX.
2. **Write `setup-auto` = `cpu`** into `%LOCALAPPDATA%\DinoTraining`.
   - A packaged start inherits no `DINO_SETUP_AUTO`, so the app also reads it from this
     file (`setup_flow.rs`).
   - A file written outside the package is visible to the package: redirected `AppData`
     reads through to the real one.
3. **Start it** through its identity; wait for `/health` (first start: Python and PyTorch
   download, up to 25 min).
4. **Find the runtime where Windows really put it**
   (`%LOCALAPPDATA%\Packages\<family>\LocalCache\Local\DinoTraining`) and import PyTorch
   there. The job summary says whether it was redirected (doc 152's question).
5. **Stop it, start it again:** `/health` without setup.
6. **`Remove-AppxPackage`,** and check that Windows removed the package's data folder with
   it: what the uninstall notice (doc 146) promises.
- **On failure, the app's logs from the redirected folder are kept** as an artifact.
