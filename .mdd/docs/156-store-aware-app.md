---
id: 156-store-aware-app
title: Store-Aware App — The App Knows It Came From the Store, and Shows Folders Where Windows Really Put Them
edition: DinoTraining
depends_on: [151-msix-package, 146-uninstall-notice]
relates: [152-msix-runtime, 59-reveal-dataset-folder, 140-error-report]
source_files:
  - apps/desktop/src-tauri/src/edition.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/desktop/src-tauri/src/error_report.rs
  - apps/desktop/src-tauri/capabilities/default.json
  - apps/frontend/src/lib/edition.ts
  - apps/frontend/src/lib/dialog.ts
  - apps/frontend/src/components/UninstallNotice.tsx
  - apps/frontend/src/i18n/en/datasets.ts
  - apps/frontend/src/i18n/de/datasets.ts
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/edition.rs
  - apps/frontend/src/lib/edition.test.ts
  - apps/frontend/src/components/UninstallNotice.test.tsx
data_flow: reads-existing
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [msix, microsoft-store, edition, package-identity, appdata-redirection, uninstall]
path: Installer/Windows/MSIX/Edition
initiative: dinotraining
wave: dinotraining-wave-15-10
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Paths the backend shows as text (e.g. a dataset's folder) are the unredirected %LOCALAPPDATA% paths; only revealing them maps to the package folder. Measured in doc 152 whether that confuses anyone."
security_read_sites: []
sister_projects: []
---

# 156 — Store-Aware App

## Purpose

- **The Store edition runs with a package identity.** Two things change for the user:
  - **Windows uninstalls it without a page of ours** and without the "delete the
    application data" box, and removes everything inside it;
  - **what it writes under `AppData` is redirected** into
    `%LOCALAPPDATA%\Packages\<family>\LocalCache\…`. The app sees it under the original
    path; Explorer, outside the package, does not.

## The edition (`edition.rs`, `app_edition`)

- **`store`** when `GetCurrentPackageFamilyName` (kernel32, no new crate) returns a
  family; **`dev`** for a debug build; else **`installer`**. Outside Windows, never
  `store`.
- **The frontend** asks once (`lib/edition.ts`, `appEdition()` / `useEdition()`); without
  a shell it is `web`; a shell without the command counts as `installer`.

## Folders shown where they really are (`reveal_path`, `shown_path`)

- **Every "Show in Explorer"** (doc 59's dataset folder, doc 145's model folder) goes
  through the shell's `reveal_path` instead of the opener plugin's `revealItemInDir`.
  - Under the Store, a path under `%LOCALAPPDATA%` or `%APPDATA%` becomes its redirected
    copy in the package folder **when that copy exists**; otherwise the path as it is (a
    folder that existed before the install is written in place).
  - Elsewhere the path is unchanged.
- **"Open the log"** (doc 140) opens the log through the same mapping.
- **The webview's `opener:allow-reveal-item-in-dir` permission is removed:** nothing in
  the frontend calls it any more.

## Wording under the Store

- **The uninstall notice** (doc 146): "Uninstalling DinoTraining in Windows removes
  everything inside it, without asking. Exported annotations and models stay where you
  saved them." The installer's sentence about the ticked box is not shown.
- **No update hint to suppress (D3):** the app has none of its own; the Store updates the
  Store edition, the download site the others.
- **The download site's Store badge** comes with doc 155, once the listing is live.

## Tests

- **Rust:** the edition rule; Local and Roaming paths map into the package folder; paths
  outside `AppData`, already inside the package, or without `%LOCALAPPDATA%` stay;
  without a package the shown path is the path.
- **Frontend:** the edition is asked once and kept, `web` without a shell, `installer`
  when the command is missing; `revealFolder` goes through `reveal_path`; the notice's
  Store wording in German, without the installer's box.
- **Under package identity:** doc 152 on the Windows runner and Jan's PCs.
