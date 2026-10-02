---
id: 143-export-targets
title: Export Targets — Each Dataset Remembers Where Its Export Goes ("With the Data" or a Folder), and When It Last Went
edition: DinoTraining
depends_on: [142-annotation-export]
relates: [144-auto-export, 146-uninstall-notice, 150-cloud-save-back]
source_files:
  - backend/app/datasets/exchange/targets.py
  - backend/app/datasets/exchange/dump.py
  - backend/app/datasets/schema.py
  - backend/app/datasets/migrations.py
  - backend/app/datasets/intake/profile.py
  - backend/app/api/v1/dataset_exchange.py
  - apps/frontend/src/api/datasetExport.ts
  - apps/frontend/src/components/DatasetExport.tsx
  - apps/frontend/src/tabs/LibraryTab.tsx
  - apps/frontend/src/lib/dialog.ts
  - apps/frontend/src/components/LibrarySection.tsx
  - apps/frontend/src/styles.css
  - apps/frontend/src/api/datasetImport.ts
  - apps/frontend/src/i18n/en/datasets.ts
  - apps/frontend/src/i18n/de/datasets.ts
routes:
  - GET /api/v1/datasets/{dataset_id}/export/target
  - PUT /api/v1/datasets/{dataset_id}/export/target
  - POST /api/v1/datasets/{dataset_id}/export
models: [datasets]
test_files:
  - backend/tests/test_export_targets.py
  - apps/frontend/src/components/DatasetExport.test.tsx
data_flow: writes-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [datasets, export, backup, folder, settings, uninstall]
path: Datasets/Export/Targets
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "`changed` reads the whole dataset to fingerprint it: cheap for thousands of pictures, a second or more for a very large one. It is asked per dataset, never for the whole list."
security_read_sites: []
sister_projects: []
---

# 143 — Export Targets

## Purpose

- **Jan (2026-10-01):**
  - "The export folder has to be asked from the user."
  - "Have 'save with the data' as an easy option for the annotations."
  - "Also remember the last saved location."
- **Doc 142 writes an export anywhere.** This doc decides where, and remembers it, so the
  button (here) and the automatic exports (doc 144) need no question.

## A dataset's target

- **Stored with the dataset:** two new columns on `datasets`, added in place (migration
  11).
  - `export_target` (JSON):
    - `kind`: `data` ("with the data") or `folder`;
    - `folder`: the chosen folder (`folder` only);
    - `include_pictures`.
  - `exported` (JSON): when, where and the content's fingerprint at the last export.
- **"With the data" is the pictures' folder** (doc 142's common parent).
  - Offered only when that folder lies **outside** the app's data folder: for pictures
    referenced in place (doc 136's default).
  - A copied, generated or example dataset lives inside the app. "With the data" would
    be removed with the app, so only a folder is offered, with "copy the pictures too"
    ticked by default (Wave 15.9, decision D2).
  - Cloud datasets get a bucket here in doc 150.
- **The fingerprint** is a SHA-256 of the export's content without its timestamps. "Has
  it changed since the last export?" is then a comparison:
  - whatever changed (a box, a phrase's variants, a check, the guideline), and however
    the row was written;
  - no write path has to remember to mark the dataset dirty.

## API

- **`GET /datasets/{id}/export/target`** →
  - `kind` and `folder` (`null` until chosen) and `include_pictures`;
  - `data_folder`: what "with the data" means here, or `null` when not offered;
  - `exported_at`, `exported_folder`;
  - `changed`: whether the content differs from the last export (`true` before the
    first).
- **`PUT /datasets/{id}/export/target`** `{kind, folder, include_pictures}`.
  - 422 for `data` where it is not offered, or `folder` without one.
- **`POST /datasets/{id}/export`:**
  - **without a body:** writes to the stored target; 422 if there is none;
  - **with `{target, include_pictures}`:** as in doc 142, and that folder becomes the
    stored target (the user chose it).
  - Either way it records `exported`.
- **`GET /datasets/profiles`** (the list) also carries `exported_at` and the target's
  folder. `changed` is not in the list: it costs a read of the whole dataset, and is
  asked per dataset.

## UI (Models & Datasets → Datasets)

- **"Export" on each dataset row** opens a small panel under the row:
  - "With the data (<folder>)", when offered;
  - "To a folder": "Choose…" opens the folder dialog **at the last folder used**,
    remembered in the app across datasets (`datasets.export.lastFolder`);
  - "Copy the pictures too";
  - "Export now". It saves the target and writes, then says where and how much.
- **The row's line** says "Exported 3 min ago · <folder>" or "Not exported yet".
- **In a browser** (no native dialog) the folder is typed, as elsewhere in the app.

## Found while building

- **The dataset list's columns were already off** (doc 136):
  - A description was a grid cell of its own, so every later cell moved one column
    over.
  - The model lists had one cell more than the grid's columns since doc 121's "Export".
  - **Fixed:** the description now sits in the parameters' cell, and the grid has a
    column for actions.
- **The panel's surface is translucent** (the app's glass look). Under a popover the
  rows below showed through, so the popover is opaque.

## Verified (2026-10-01)

- **Backend (1938 tests, 4 new):**
  - "with the data" offered only for pictures outside the app; a copied dataset
    defaults to copying its pictures and refuses "with the data";
  - an empty folder is refused;
  - an export is remembered;
  - `changed` turns true for a phrase (no picture touched) and for the guideline file;
  - the bookkeeping itself is not a change;
  - the API:
    - 422 without a target;
    - a folder chosen, then written;
    - the profile carries the last export;
    - an unwritable folder is refused **and not remembered**;
    - 422 for an unknown kind; 404.
  - A restore does not inherit the original's export target.
- **Frontend (1163 tests, 4 new):**
  - "with the data" chosen by default and exported there;
  - a dataset inside the app:
    - asks for a folder, opening at the last one;
    - copies the pictures by default;
    - remembers the folder;
  - a refusal shown;
  - "3 minutes ago" / "gestern" / "vor 2 Minuten".
  - The button stays disabled until the target has loaded (CLAUDE.md's async rule).
- **Live (German UI, the real backend, schema migrated to 11 in place):**
  - **OSDaR23 · RGB centre** (pictures inside the app):
    - the panel says so, with "Die Bilder mitkopieren" ticked;
    - exported to a folder: "Geschrieben nach …/ui-export/dinotraining: 10 Bilder ·
      300 Objekte";
    - the row then read "Exportiert vor 41 Sekunden".
  - **Wave 12 filled-ring** (pictures in place):
    - "Bei den Daten (<its folder>)" offered and chosen;
    - the folder field already held the last folder used.
  - **The list:** every row in one line, the model list too.
  - The test target was cleared from the real library afterwards.
