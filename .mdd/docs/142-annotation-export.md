---
id: 142-annotation-export
title: Annotation Export — Everything a Dataset Knows, Written Beside Its Pictures, and Restored by Importing
edition: DinoTraining
depends_on: [136-dataset-import, 31-external-dataset-import]
relates: [143-export-targets, 144-auto-export, 150-cloud-save-back]
source_files:
  - backend/app/datasets/exchange/__init__.py
  - backend/app/datasets/exchange/layout.py
  - backend/app/datasets/exchange/dump.py
  - backend/app/datasets/exchange/restore.py
  - backend/app/datasets/exchange/export.py
  - backend/app/datasets/intake/detect.py
  - backend/app/datasets/intake/importer.py
  - backend/app/api/v1/dataset_exchange.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/components/DatasetImport.tsx
  - apps/frontend/src/api/datasetImport.ts
  - apps/frontend/src/i18n/en/datasets.ts
  - apps/frontend/src/i18n/de/datasets.ts
routes:
  - POST /api/v1/datasets/{dataset_id}/export
models: [datasets, images, boxes, masks, dataset_classes, phrases, mask_phrases, image_phrase_status, phrase_classes]
test_files:
  - backend/tests/test_exchange.py
  - apps/frontend/src/components/DatasetImport.test.tsx
data_flow: reads-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [datasets, export, restore, backup, coco, annotations, uninstall]
path: Datasets/Export
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**Pictures on two Windows drives** share no folder: their paths travel absolute, so such an export restores only where those paths still exist."
  - "Restored pictures are referenced where they were found (copy_images off), even if the original dataset had copied them into the app."
security_read_sites:
  - backend/app/datasets/exchange/restore.py (picture paths from an export file become file paths; they must stay inside the pictures' folder)
sister_projects: []
---

# 142 — Annotation Export

## Purpose

- **Jan (2026-10-01):** "work in the database to keep the speed and export into the
  data folder". Nothing a user made should live only inside the app, which an
  uninstall removes (and under MSIX, Wave 15.10, removes without asking).
- **This feature is the export and the restore.** Where it goes and when it runs are
  docs 143 and 144.

## What is written: `<target>/dinotraining/`

- **`dinotraining.json`:** the whole dataset, format `dinotraining-export` version 1.
  - **Every row of every table that belongs to the dataset:** the dataset itself, its
    pictures, boxes, masks, classes, phrases, which phrases a mask answers to, the
    per-picture checks ("complete" / "absent") and umbrella terms' classes.
  - **Read with `SELECT *`.** A column added later travels without changing this code;
    a column the restoring app does not know is dropped with a warning; a missing
    one takes its default.
  - **Row ids are kept only as references between rows.** A restore gives new ids
    and remaps them.
  - **Picture paths are relative to the pictures' folder** (their common parent), so a
    moved folder or another machine still matches. The original folder is kept as a
    hint.
  - **Never-saved pictures** (doc 136, `annotated_at = ''`) travel as they are.
  - **The dataset's state files**, inline:
    - the guideline (`guideline.md`);
    - the split settings, the preparation state, the annotation target and the second
      look;
    - the recipes, with their `dataset_id` rewritten on restore.
    - `audit.json` is not exported: it is recomputed.
  - **Who wrote it:** the export's time and the app version.
- **`annotations.coco.json`,** for other tools: boxes and masks of the saved pictures (doc
  31's builder). Its `file_name`s are relative to the pictures' folder, which its `info`
  says. The restore never reads it; `dinotraining.json` is the whole truth.
- **Optionally `pictures/`:** a copy of the pictures. For a dataset whose pictures live
  inside the app (doc 143 offers it), so the export is complete without the app.
- **Written atomically:** each file goes to a temporary name, then is renamed over the
  old one. An export cut off by closing the app leaves the previous export whole.

## Restore = import (doc 136)

- **Detection** recognises a folder holding `dinotraining/dinotraining.json` (or the
  `dinotraining` folder itself). It reports kind `dinotraining`, with the counts from the
  file, before anything else is tried.
- **The pictures' folder, in this order:**
  1. `dinotraining/pictures/`, if the export copied the pictures;
  2. the folder that holds `dinotraining/` (the "with the data" case: the folder was
     moved, or this is another machine);
  3. the original folder named in the file.
  - The first where the first picture exists wins. If none has it, detection says so.
- **A path that would leave the pictures' folder (`..`) is refused.**
- **One transaction:** a restore that fails leaves no half dataset (as doc 136).

## API

- **`POST /datasets/{id}/export`** `{target, include_pictures}` writes the export.
  - Answers `{folder, pictures, annotated, objects, written_at}`.
  - 404 for an unknown dataset; 422 for a target that cannot be written.
- **The existing `POST /datasets/{id}/export/coco` stays** (doc 31). It writes into the
  app's own folder, as before.

## In the import screen

- **The kind is worded:** "a DinoTraining export (restored completely)".
- **"Copy pictures" is hidden:** a restore references the pictures where it finds them.
- **When the pictures are nowhere,** the note says where it looked, and "Import" is
  disabled.

## Verified (2026-10-01)

- **Backend (1934 tests, 6 new):**
  - **A fully filled dataset** (boxes, masks, a never-saved picture, splits, classes,
    a phrase with variants and a confusable, an umbrella term, a mask's phrase, an
    "absent" check, an excluded frame, the guideline, a recipe):
    - exported "with the data";
    - the folder moved;
    - detected as `dinotraining` ahead of its own old COCO files;
    - restored. Every table is equal row for row, references remapped, and the
      recipe's `dataset_id` rewritten.
  - **Copied pictures** restore with the originals deleted.
  - **Missing pictures:** named, refused, nothing left behind.
  - **Refused:**
    - a newer format;
    - a path that leaves the folder (with nothing left behind).
  - **A column unknown to this app** is dropped, and the rest restores.
  - **An interrupted write** keeps the previous file, and no temporary file is left.
  - **The API:** 200, 404, and a 422 that says why.
- **Frontend (1159 tests, 1 new):** the kind, the note, the hidden checkbox, the
  disabled button.
- **Live (German UI, the real backend):**
  - OSDaR23 · RGB centre exported through the API with its pictures (10 pictures, 300
    objects, 54 MB);
  - Models & Datasets → Datasets → the export's folder: "Gefunden: ein
    DinoTraining-Export (wird vollständig wiederhergestellt) · 10 Bilder · 10 annotiert
    · 300 Objekte · 6 Klassen";
  - imported under a new name;
  - compared with the original in the live database: images 10 and boxes 300
    identical, the state files identical, the pictures read from the export's
    `pictures/`;
  - the test copy deleted again.
