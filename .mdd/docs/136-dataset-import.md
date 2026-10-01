---
id: 136-dataset-import
title: Dataset Import — Any Folder or Video, Detected, Described, with Its Parameters Saved
edition: DinoTraining
depends_on: [135-models-datasets-tab, 31-external-dataset-import, 49-osdar23-rail, 82-intake-check]
relates: [137-dataset-guide, 138-osdar23-example]
source_files:
  - backend/app/datasets/intake/detect.py
  - backend/app/datasets/intake/convert_yolo.py
  - backend/app/datasets/intake/convert_voc.py
  - backend/app/datasets/intake/importer.py
  - backend/app/datasets/intake/profile.py
  - backend/app/datasets/coco_import.py
  - backend/app/datasets/openlabel_to_coco.py
  - backend/app/datasets/schema.py
  - backend/app/datasets/store.py
  - backend/app/datasets/models.py
  - backend/app/api/v1/dataset_import.py
  - backend/app/mcp/prep_tools.py
  - apps/frontend/src/components/DatasetImport.tsx
  - apps/frontend/src/api/datasetImport.ts
  - apps/frontend/src/tabs/ModelsTab.tsx
routes:
  - POST /api/v1/datasets/import/detect
  - POST /api/v1/datasets/import
  - GET /api/v1/datasets/{dataset_id}/profile
models: [datasets, images, boxes, masks]
test_files:
  - backend/tests/test_intake_detect.py
  - backend/tests/test_intake_import.py
  - backend/tests/test_dataset_profile.py
  - apps/frontend/src/components/DatasetImport.test.tsx
data_flow: writes-existing
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [datasets, import, coco, yolo, pascal-voc, openlabel, video, metadata]
path: Datasets/Import
initiative: dinotraining
wave: dinotraining-wave-15-8
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
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
  complete, doc 117). A picture without one is not. This holds for every format,
  including pictures-only and video.

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
