---
id: 136-dataset-import
title: Dataset Import — Any Folder or Video, Detected, Described, with Its Parameters Saved
edition: DinoTraining
depends_on: [135-models-datasets-tab, 31-external-dataset-import, 49-osdar23-rail, 82-intake-check]
relates: [137-dataset-guide, 138-osdar23-example]
source_files:
  - backend/app/datasets/intake/detect.py
  - backend/app/datasets/intake/walk.py
  - backend/app/datasets/intake/documents.py
  - backend/app/datasets/intake/yolo.py
  - backend/app/datasets/intake/voc.py
  - backend/app/datasets/intake/segmentation.py
  - backend/app/datasets/intake/details.py
  - backend/app/datasets/intake/jobs.py
  - backend/app/datasets/intake/importer.py
  - backend/app/datasets/images.py (NEVER_SAVED)
  - backend/app/ml/training/sample_prep.py
  - backend/app/prep/stats.py
  - backend/app/prep/task_facts.py
  - backend/app/datasets/completeness.py
  - backend/app/api/v1/datasets.py (export)
  - backend/app/api/v1/router.py
  - backend/app/mcp/dataset_import_tools.py
  - apps/frontend/src/hooks/useDatasetProfiles.ts
  - apps/frontend/src/tabs/LibraryTab.tsx
  - apps/frontend/src/components/LibrarySection.tsx
  - backend/app/datasets/intake/profile.py
  - backend/app/datasets/coco_import.py
  - backend/app/datasets/openlabel_to_coco.py
  - backend/app/datasets/schema.py
  - backend/app/datasets/store.py
  - backend/app/datasets/models.py
  - backend/app/api/v1/dataset_import.py
  - apps/frontend/src/components/DatasetImport.tsx
  - apps/frontend/src/api/datasetImport.ts
  - apps/frontend/src/tabs/ModelsTab.tsx
routes:
  - POST /api/v1/datasets/import/detect
  - POST /api/v1/datasets/import
  - GET /api/v1/datasets/import/jobs/{job_id}
  - GET /api/v1/datasets/profiles
  - GET /api/v1/datasets/{dataset_id}/profile
models: [datasets, images, boxes, masks]
test_files:
  - backend/tests/test_intake_detect.py
  - backend/tests/test_intake_import.py
  - backend/tests/intake_fixtures.py
  - apps/frontend/src/components/DatasetImport.test.tsx
data_flow: writes-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [datasets, import, coco, yolo, pascal-voc, openlabel, video, metadata]
path: Datasets/Import
initiative: dinotraining
wave: dinotraining-wave-15-8
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "A video is sampled to at most 3 000 frames (evenly); longer recordings lose frames by design. A setting for it, if asked."
  - "Pictures imported without annotations are 'never saved' (annotated_at = ''): the images table requires a value, and '' sorts before every timestamp. Every training, export and preparation reader filters them; a new reader of the images table must too."
security_read_sites: []
sister_projects: []
---

# 136 — Dataset Import

## Purpose

- **Jan (2026-10-01):** "a tab/section to use a downloaded dataset and make it a dataset
  for the tool".
  - Like opening a folder in the other tabs.
  - Saved as a dataset with or without annotations.
  - An optional description.
  - The parameters saved automatically: created, images or video, number of images,
    with or without annotations, how many are annotated, how many classes, what type of
    annotations.
- **What existed:** a COCO importer (doc 31) and an intake check (doc 82) behind the API
  and MCP, never in the UI. COCO's polygons and RLE masks were ignored. OpenLABEL could
  be converted but not imported, because the converted images carried no size.

## The flow (Models & Datasets → Datasets → "Import a dataset")

1. **Pick** a folder (or a video file) with the native dialog, or type the path.
2. **Detect** (`POST /datasets/import/detect`). The answer shows:
   - the format;
   - the pictures, the annotation files and the annotated pictures;
   - the classes;
   - the annotation types (boxes, masks);
   - the splits;
   - anything doubtful (doc 82's box-convention evidence for COCO).
3. **Name** (default: the folder's name) and an optional **description**.
4. **Copy pictures** into the app's data folder, or reference them in place (the
   Studio's default).
5. **Import** (`POST /datasets/import`). The new dataset appears in the list with its
   parameters.

## Formats detected (`intake/detect.py`)

| Format | Recognised by | Imported as |
|---|---|---|
| Pictures only | image files, no annotation files | pictures, not annotated |
| Video | a video file (or a folder of them) | frames (doc 73's extraction, every frame up to a cap), grouped as a sequence, not annotated |
| COCO | a JSON with `images`, `annotations`, `categories` (`_annotations.coco.json` per split, or any name) | boxes; **polygons and RLE → masks** |
| YOLO | `labels/*.txt` with `class cx cy w h` (or polygons), `data.yaml` or `classes.txt` | boxes; polygons → masks |
| Pascal VOC | `Annotations/*.xml` with `<object><bndbox>` | boxes |
| OpenLABEL | a JSON with a top-level `openlabel` (OSDaR23) | boxes per chosen camera (doc 49's reader; sizes read from the pictures) |
| Unknown or mixed | anything else | refused, with what was found and what is expected |

- **Every annotated format goes through one path:** converted into a COCO document in
  memory, then doc 31's importer. That path:
  - resolves classes by name;
  - skips boxes outside the picture;
  - takes splits from folder names.
- **Annotations arrive as `positive`, provenance `imported`** (doc 31).
- **A picture with an annotation file is "annotated"** (`annotated_at` set: saved means
  complete, doc 117). A picture without one is **never saved**:
  - `annotated_at = ''` (`NEVER_SAVED`): the column is NOT NULL, and `''` sorts before
    every class, so doc 117 reads the picture as unknown;
  - head training (which reads a picture without boxes as pure background), the COCO
    export, the preparation counts and doc 118's "saved before the class" list all
    leave it out;
  - saving it in the Studio gives it a real time, and then it counts.
  - **Found while building:** without this, an imported folder of 1 000 unannotated
    pictures would have trained as 1 000 "nothing here" examples.

## The parameters (`GET /datasets/{id}/profile`, and in the list)

- **Stored:** `description` and `source` (where it was imported from) are new nullable
  columns, added in place by the migration runner, and are also in `dataset.json`.
- **Computed live from the store,** so they never go stale:
  - created;
  - media (`images`, `video`, `mixed`);
  - pictures;
  - annotated pictures;
  - classes (count and names);
  - annotation types (`boxes`, `masks`).
- **Also written into `dataset.json` at import,** as the dataset's own record of what
  arrived.
- **The Datasets list** shows the description and a line such as "1 284 pictures · 1 102
  annotated · 3 classes · boxes, masks · video".

## MCP

- `detect_dataset(path)` and `import_dataset(path, name, description, copy_images)`
  mirror the endpoints.
- The COCO-only tools stay for compatibility.

## Verified (2026-10-01)

- **Backend (1913 tests in all, 18 new):**
  - detection per format:
    - COCO splits (`valid` normalised to `val`), only the classes that are used (not
      Roboflow's placeholder), boxes and masks, the picture in no file;
    - YOLO with `data.yaml` names and polygon lines;
    - VOC boxes;
    - OpenLABEL per camera, track excluded, sizes read from the pictures;
    - plain pictures and a real 12-frame video;
    - an empty folder says what was expected; a folder over the file limit is refused
      instead of walked;
  - pycocotools' compressed RLE round-trips against its own encoder (`rleToString`) for
    four runs, including a real square mask;
  - import per format with the counts, masks stored as `imported`, never-saved flags,
    the manifest's description, source and record, and a failed import leaving no
    dataset;
  - the API: detect, a 422 for a missing path, a background job polled to completion,
    the profile (one and all), 404s;
  - never-saved pictures are excluded from training until saved, then included; not in
    doc 118's unknown list; not in the COCO export (3 of 4 pictures).
- **Found while building:**
  - `annotated_at` is NOT NULL, so unannotated pictures cannot be `NULL`. That raised
    the real question: what training does with them (see above).
  - `GET /datasets/profiles` was answered by `GET /datasets/{dataset_id}` (a dataset
    called "profiles"): the import router is now mounted first, and the test pins it.
- **Frontend (1141 tests):**
  - the component (5): the summary before import; the name from the folder unless
    typed, with the description sent; the job followed to "imported" and the list
    re-read once; an unreadable folder's reason; German;
  - the catalogue keeps format names (YOLO, Pascal VOC, OpenLABEL) as they are.
- **Live, in the running app (German), on the real backend:**
  - Models & Datasets → Datensätze → a COCO folder:
    - "Gefunden: COCO · 4 Bilder · 3 annotiert · 3 Objekte · 2 Klassen · Boxen, Masks
      · Splits: train, val";
    - imported with a description;
    - the list re-read itself with "4 Bilder · 3 annotiert · 2 Klassen · … · Bilder" and
      the description under it.
  - Through the API: the YOLO folder (3 pictures, 1 mask from a polygon), and a
    40-frame video (one sequence, 40 frames, media `video`).
  - Found live: the detection's notes came as English sentences into the German UI;
    they are now codes the UI words, and "boxes, masks" became "Boxen, Masks".
  - The three test datasets were deleted again (the library is back to 18).
