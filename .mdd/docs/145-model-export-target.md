---
id: 145-model-export-target
title: Model Export Target — Trained Models Export to a Remembered Folder, by Hand or When Their Training Finishes
edition: DinoTraining
depends_on: [121-export-bundle, 144-auto-export]
relates: [146-uninstall-notice]
source_files:
  - backend/app/mlops/auto_export.py
  - backend/app/mlops/tracking_hooks.py
  - backend/app/finetune/runner.py
  - backend/app/main.py
  - backend/app/core/config.py
  - backend/app/api/v1/exports.py
  - apps/frontend/src/api/exports.ts
  - apps/frontend/src/components/ModelExportActions.tsx
  - apps/frontend/src/components/ModelAutoExport.tsx
  - apps/frontend/src/tabs/ModelsTab.tsx
  - apps/frontend/src/i18n/en/datasets.ts
  - apps/frontend/src/i18n/de/datasets.ts
routes:
  - GET /api/v1/exports/settings
  - PUT /api/v1/exports/settings
models: [head_instances]
test_files:
  - backend/tests/test_model_auto_export.py
  - backend/tests/test_finetune_runner.py
  - apps/frontend/src/components/ModelAutoExport.test.tsx
data_flow: reads-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [models, export, backup, auto-export, heads, fine-tuning, uninstall]
path: Models/Export/Target
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "A head's training is not repeated in this check: the hook's own function exported a real trained head, and the hook's wiring (saved → export) is pinned by tests. A full training run with the setting on was not made."
security_read_sites: []
sister_projects: []
---

# 145 — Model Export Target

## Purpose

- **Jan (2026-10-01):** "The export button for trained models saves the model", with an
  auto export as for annotations.
- **A trained model does not change after its training**, so "every n minutes" means
  nothing for it. It is exported once, when it is made, or by hand.

## By hand (doc 121's "Export")

- **The folder dialog opens at the last folder a model was exported to**
  (`models.export.lastFolder`, remembered in the app), and that folder is remembered
  again.

## When a training finishes

- **Setting:** "Export each trained model when its training finishes", to a folder.
  - **`.env`:** `DINO_MODEL_EXPORT_FOLDER`. Empty means off, the default (Wave 15.9,
    decision D3).
  - **Through `GET` / `PUT /exports/settings`** (doc 144): a `model_folder` field.
    A `PUT` without the field leaves it as it is.
- **Heads:** a job hook (as MLflow's, doc 123) listens for `saved`.
- **Fine-tuned models:** the runner calls the same function after its model is saved.
- **The export is doc 121's bundle** (`<name>.zip` with card, weights, runtime and
  ONNX for a head).
  - It runs in a thread of its own, so the next training does not wait for it.
  - What it wrote, or why it could not, goes into the job's notes, which the Training
    tab shows, and the log.

## UI (Models & Datasets → My Models, above the list)

- **"Export trained models automatically":**
  - a checkbox and the folder ("Choose…" opens at the last model folder);
  - saved on change.

## Found while building

- **MLflow's test** "without MLflow nothing is attached" found this hook attaching a
  listener to every job.
- **It now decides when the job starts:** off means no listener at all.

## Verified (2026-10-01)

- **Backend (1949 tests, 6 new):**
  - off by default and for a blank folder;
  - the bundle goes into the folder (created when missing), and the note says where;
  - a failed export is a note, not a crash;
  - a head is handed over on `saved` only, never on "epoch" or "finish";
  - the hook registers once and attaches nothing when off;
  - a completed fine-tune is handed over with its id;
  - the API:
    - `model_folder` set, kept when absent, cleared with `null`;
    - a relative path refused with nothing written.
- **Frontend (1171 tests, 3 new):**
  - the toggle is disabled until there is a folder;
  - switched on with the folder, the other settings kept;
  - the last model folder offered;
  - switching off clears only the folder;
  - a refusal shown, in German.
- **Live:**
  - **My Models:** "Trainierte Modelle automatisch exportieren", a folder typed and
    switched on. It was written to a scratch `.env` (Jan's `.env` untouched).
  - **The hook's own function** on the latest trained head ("Object detection: person
    +2 more"):
    - the real bundle with ONNX, 81 MB, written in 6.2 s;
    - the note "Exported to …/Object_detection_person_2_more.zip".
  - The backend was restarted on the real `.env` afterwards.
