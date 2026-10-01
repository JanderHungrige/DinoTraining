---
id: 144-auto-export
title: Auto-Export — On Closing the App and Every n Minutes, Only What Changed
edition: DinoTraining
depends_on: [143-export-targets]
relates: [146-uninstall-notice, 150-cloud-save-back]
source_files:
  - backend/app/datasets/exchange/auto.py
  - backend/app/api/v1/exports.py
  - backend/app/api/v1/router.py
  - backend/app/core/config.py
  - apps/desktop/src-tauri/src/lib.rs
  - apps/desktop/src-tauri/src/auto_export.rs
  - apps/desktop/src-tauri/src/sidecar.rs
  - apps/frontend/src/api/exports.ts
  - apps/frontend/src/hooks/useAutoExport.ts
  - apps/frontend/src/components/AutoExportSettings.tsx
  - apps/frontend/src/App.tsx
  - apps/frontend/src/tabs/ModelsTab.tsx
routes:
  - GET /api/v1/exports/settings
  - PUT /api/v1/exports/settings
  - GET /api/v1/exports/status
  - POST /api/v1/exports/run
models: [datasets]
test_files:
  - backend/tests/test_auto_export.py
  - apps/desktop/src-tauri/src/auto_export.rs
  - apps/frontend/src/components/AutoExportSettings.test.tsx
  - apps/frontend/src/i18n/en/datasets.ts
  - apps/frontend/src/i18n/de/datasets.ts
data_flow: reads-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [datasets, export, backup, auto-export, settings, shutdown, tauri]
path: Datasets/Export/Auto
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**Quitting the real desktop window was not clicked** (this session cannot drive a native window). The shell's code compiles and its unit tests pass; the request it sends was sent by hand to the live backend and answered as expected."
  - "The settings box shows the last run when it is opened or after its own 'Export all now'; it does not follow interval runs live."
security_read_sites: []
sister_projects: []
---

# 144 — Auto-Export

## Purpose

- **Jan (2026-10-01):** "a checkbox with auto export of model / annotations on app
  closing or every n minutes".
- **Defaults** (Wave 15.9, decision D3):
  - on closing **on**;
  - every 10 minutes **off**.

## One run, three callers

- **`POST /exports/run`** exports every dataset that has a target (doc 143) and whose
  content changed since its last export.
  - **Skipped and reported:** datasets without a target (with their names, so the app can
    remind), and datasets without changes.
  - **One run at a time.** A second call while one runs says so instead of starting
    another.
  - **`deadline_seconds`:** a dataset that would start after it is left for the next run
    and reported as unfinished. A dataset already writing is never cut off; doc 142's
    atomic writes keep the previous export whole either way.
  - **`wait`:** `true` (closing) answers with the report; `false` (the interval) starts
    the run in the background and answers at once.
- **The report of the last run is kept** in the data folder (`auto_export.json`). The app
  names, at its next start, what failed or did not finish on closing.

### Callers

1. **Closing the desktop app** (`auto_export.rs`):
   - On `ExitRequested`, the shell holds the exit once and asks the backend to run with
     a deadline of 20 s.
   - It waits at most 25 s for the answer, then stops the backend and exits.
   - The setting is the backend's. With "on closing" off, the run answers at once.
   - A second quit while it waits exits at once.
2. **Every n minutes** (`useAutoExport`): while the app is open, the window asks for a
   background run every n minutes when the interval is on.
   - The interval lives where the user is, not in a backend timer. A backend nobody looks
     at has nothing new to export.
3. **"Export all now"** in the settings box and in doc 146's notice.

## Settings

- **`.env`, beside the other settings:**
  - `DINO_EXPORT_ON_CLOSE` (default `true`);
  - `DINO_EXPORT_EVERY_MINUTES` (default `0` = off; 1–1440 when on).
- **`GET` / `PUT /exports/settings`.**
- **UI (Models & Datasets → Datasets, above the list): "Automatic export":**
  - "When closing the app" and "Every [10] minutes";
  - "Export all now";
  - a line on the last run: when, what was exported, what failed, and which datasets
    have no target yet.

## Not here

- **A browser tab (web mode) closing** cannot hold the page for an export. Only the
  desktop app exports on closing; the interval works in both.
- **Trained models** export on finishing a training (doc 145), not here: they do not
  change afterwards.

## Verified (2026-10-01)

- **Backend (1943 tests, 5 new):**
  - only a dataset with a target and changes goes; one without a target is named;
  - a second run says "unchanged";
  - a split change is a change again;
  - the report is kept;
  - a deadline (a mocked clock) leaves the second dataset unfinished;
  - an unwritable target is reported while the others still go;
  - one run at a time, for the background start too;
  - the API: settings default, `.env` written, closing with the setting off answers
    "off", a closing run reports, status, 422s.
  - **Found by a test:** the background start checked the "running" flag, not the
    lock. A run holding the lock could still be answered "started". It now takes the
    lock first.
- **Rust (46 tests, 2 new):**
  - the exit is held once;
  - the request's body (deadline 20 s, wait 25 s) and its log line;
  - clippy clean.
- **Frontend (1168 tests, 5 new):**
  - the last closing's failures, unfinished and target-less datasets named;
  - settings saved, with the interval told;
  - "Export all now" re-reads the list;
  - German;
  - the interval fires every n minutes only when on.
- **Live (German UI, the backend on a scratch `.env`; the worktree's `.env` is a link to
  Jan's real one):**
  - "Automatischer Export" with the defaults (on closing on, interval off);
  - one dataset given a target, then "Jetzt alle exportieren": "Letzter Lauf jetzt: 1
    exportiert, 0 unverändert", and the 15 datasets without a target named;
  - **the shell's closing request sent by hand:** `done`, 0 exported, 1 unchanged, 15
    without a target;
  - "Alle 10 Minuten" switched on: written to the scratch `.env` only (Jan's `.env` has
    no `DINO_EXPORT_*`).
  - The test target and report were cleared from the real library, and the backend was
    restarted on the real `.env`.
