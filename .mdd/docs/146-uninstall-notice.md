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
status: complete
phase: all
mdd_version: 11
tags: [uninstall, export, backup, notice, nsis, windows, msix]
path: Datasets/Export/Uninstall Notice
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**The uninstaller's message box was not seen on a real Windows desktop.** The release dry run built the installer with the hook and removed it silently (the box is skipped there by design); the box itself needs one manual uninstall with 'Delete the application data' ticked."
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

## Found while building

- **The EXE uninstaller removes the user's data only with "Delete the application data"
  ticked** (doc 132). So:
  - the message box appears only then;
  - the in-app text says "**can** remove everything … (from the Windows installer when
    you tick …)", not "removes everything".
- **"Export everything now" can only export datasets that have a target.**
  - With 16 datasets and no targets, the button would have done nothing.
  - It now appears only for changes that can go. Datasets without a target are told how
    to get one.
- **The hooks file needed a UTF-8 BOM:** NSIS reads an included file without one as
  ANSI, and the German umlauts would have been garbled.

## Verified (2026-10-01)

- **Backend (1951 tests, 2 new):**
  - work without a target named;
  - a picture with no save is no work;
  - a change after an export named;
  - the API's answer.
- **Frontend (1175 tests, 4 new):**
  - the lead;
  - names with counts (one/many) and how to give a target;
  - "Export everything now" re-reads to "All datasets are exported";
  - no button when nothing can go;
  - the warning survives an unavailable backend;
  - German.
- **Live (the real library):**
  - the overview answered in 0.07 s for 16 datasets and 25 models;
  - the notice named all 16, told how to give them a target, and showed no button.
- **CI:**
  - release dry run 36869568457 on the branch, green on all three platforms;
  - the Windows installer built with the hook and the BOM;
  - doc 131's silent uninstall still removed it.
