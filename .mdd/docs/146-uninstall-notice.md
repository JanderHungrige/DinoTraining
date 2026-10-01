---
id: 146-uninstall-notice
title: Uninstall Notice — Say Before It Matters That Uninstalling Removes What Is Inside the App, and What Is Not Yet Exported
edition: DinoTraining
depends_on: [144-auto-export, 145-model-export-target, 132-uninstall]
relates: [151-msix-package]
source_files:
  - backend/app/datasets/exchange/overview.py
  - backend/app/api/v1/exports.py
  - apps/frontend/src/api/exports.ts
  - apps/frontend/src/components/UninstallNotice.tsx
  - apps/frontend/src/tabs/ModelsTab.tsx
  - apps/frontend/src/i18n/en/datasets.ts
  - apps/frontend/src/i18n/de/datasets.ts
  - apps/frontend/src/styles.css
  - apps/desktop/src-tauri/windows/hooks.nsh
routes:
  - GET /api/v1/exports/overview
models: [datasets, head_instances]
test_files:
  - backend/tests/test_export_overview.py
  - apps/frontend/src/components/UninstallNotice.test.tsx
data_flow: reads-existing
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [uninstall, export, backup, notice, nsis, windows, msix]
path: Datasets/Export/Uninstall Notice
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 146 — Uninstall Notice

## Purpose

- **Jan (2026-10-01):** "A warning that with uninstalling all data disappears but can be
  exported via …".
- **Under MSIX (Wave 15.10)** Windows removes the app's folders on uninstall, with no
  page of the app's own to warn from. The warning must be in the app, where the work is.

## In the app (Models & Datasets, above the sub-tabs)

- **"Everything inside DinoTraining is removed when you uninstall it. Exported
  annotations and models stay where you saved them."**
- **The state, in one line, from `GET /exports/overview`:**
  - datasets with work in them (at least one saved picture) and **no export target**;
  - datasets with a target but **changes not yet exported**;
  - trained models, and whether they export by themselves (doc 145).
  - When nothing is pending, it says so ("All datasets are exported").
- **"Export everything now":** doc 144's run. It re-reads the state afterwards.
- **Shown in both sub-tabs**, small; it never blocks anything.

## The EXE uninstaller (doc 132's hooks)

- **Before removing anything, a message box:**
  - it says the same, in English and German, and that exports stay;
  - OK continues, Cancel leaves everything installed.
- **Not when:**
  - updating (doc 132: an update reinstalls and keeps everything);
  - silent (`/S`: doc 131's smoke test and unattended removals).

## API

- **`GET /exports/overview`:**
  - `datasets` (with work);
  - `no_target` and `unexported` (names);
  - `models` (count);
  - `model_folder` (doc 145's setting).
  - It fingerprints every dataset with a target, so it is asked when the notice is
    shown, not polled.
