---
id: 137-dataset-guide
title: Dataset Guide — How a Downloaded Dataset Must Be Laid Out, per Format, and Where to Find Datasets
edition: DinoTraining
depends_on: [136-dataset-import]
relates: [138-osdar23-example, 48-dataset-format-guide, 59-reveal-dataset-folder]
source_files:
  - apps/frontend/src/components/DatasetGuide.tsx
  - apps/frontend/src/tabs/ModelsTab.tsx
  - apps/frontend/src/i18n/en/guide.ts
  - apps/frontend/src/i18n/de/guide.ts
  - apps/frontend/src/i18n/catalogue.ts
  - apps/frontend/src/styles.css
  - apps/desktop/src-tauri/capabilities/default.json
routes: []
models: []
test_files:
  - apps/frontend/src/components/DatasetGuide.test.tsx
data_flow: greenfield
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [datasets, import, guide, coco, yolo, pascal-voc, openlabel, osdar23]
path: Datasets/Guide
initiative: dinotraining
wave: dinotraining-wave-15-8
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**The https permission was never clicked in the real desktop app** (as in doc 59, this session cannot drive a native webview). The opener plugin's own click handler and its permission check were read in its source, and `cargo check` validates the capability."
security_read_sites: []
sister_projects: []
---

# 137 — Dataset Guide

## Purpose

- **Jan (2026-10-01):**
  - "an explaining text how a dataset that is downloaded has to be saved to be
    importable": easy without annotations, but what must the structure look like with
    annotations, for the different types?
  - and references to known dataset sites, OSDaR23 from Deutsche Bahn among them.

## Where

- **In the Datasets sub-tab, below the import:** two folded sections.
  - **"How must a dataset look?"**
  - **"Where to find datasets"**
- **Folded,** because the list is what a returning user wants first.
- Doc 48's COCO guide in the Training tab stays: it explains what *training* needs.
  This one explains what the *import* reads.

## What it says, per format (as doc 136 reads them)

- **Without annotations:** a folder of pictures (JPEG, PNG, BMP, WebP, TIFF, GIF, up to
  five folder levels deep), or a video (MP4, MOV, AVI, MKV, WebM, M4V). Imported for
  annotating in the app.
- **COCO** (Roboflow, Hugging Face, CVAT and most tools):
  - one JSON per split, with `images`, `annotations` and `categories`;
  - `file_name` relative to the JSON's folder;
  - `bbox` `[x, y, w, h]` in pixels;
  - `segmentation` polygons or RLE become masks.
- **YOLO** (Ultralytics, Roboflow "YOLOv5/v8"):
  - `images/<split>/x.jpg` with `labels/<split>/x.txt`;
  - `class cx cy w h`, normalised to 0–1; a longer line is a polygon (→ a mask);
  - class names in `data.yaml` (`names:`) or `classes.txt`;
  - a picture without a `.txt` has no objects.
- **Pascal VOC:** `Annotations/x.xml` with `<object><name>` and `<bndbox>`, pictures in
  `JPEGImages/`.
- **OpenLABEL** (OSDaR23):
  - the sequence folder with its `*_labels.json` and one folder per camera
    (`rgb_center/`, …);
  - each picture camera's pictures are imported; lidar and radar are ignored;
  - `track` polylines are left out (doc 49).
- **Splits:** a folder named `train`, `val`/`valid` or `test` anywhere on the way
  becomes the split.
- **Each format with a small folder tree**, in monospace. The trees are not translated;
  the explanations are.

## Where to find datasets

| Site | What | Export to choose |
|---|---|---|
| Hugging Face Datasets | many vision sets, filter "object detection" / "image segmentation" | COCO or YOLO, where offered |
| Roboflow Universe | many community-annotated sets | COCO JSON or YOLOv8 |
| Kaggle Datasets | competitions and community sets | as published |
| Open Images V7 | 9 M pictures, 600 classes, boxes and masks | its CSV (convert to COCO first) |
| COCO | the reference set: 80 classes, boxes and masks | as published |
| OSDaR23 (Deutsche Bahn, Digitale Schiene Deutschland) | rail multi-sensor set: cameras, lidar, radar, 20 classes | OpenLABEL, imported directly; see doc 138 |

- **Licences:** each dataset has its own. Check it before training on it, or before
  sharing a model trained on it.
  - **OSDaR23:** **CC BY-SA 3.0 DE**, read from the portal's CKAN API while building
    doc 138, which shows it with the example.
  - **COCO:** the annotations are CC BY 4.0; the pictures are under Flickr's terms.

## Links in the desktop app (found while building)

- **Every `target="_blank"` link was dead in the desktop app.** Tauri's opener plugin
  intercepts the click and calls `opener|open_url`. The capability granted only
  `reveal-item-in-dir` (doc 59), so the call was refused and nothing opened. That
  included the existing licence links on the model cards and in the token panel.
- **Now granted** `opener:allow-open-url`, scoped to `https://*` only: `http:`, `mailto:`
  and `tel:` stay refused, because the app links nothing else.

## Verified (2026-10-01)

- **Frontend (1145 tests, 4 new):**
  - both sections folded;
  - every format with its heading and its tree;
  - the sites linked in a new window, `https` only, OSDaR23 with its data portal;
  - German, with the trees unchanged.
- **Live (browser pane, German and English):**
  - Models & Datasets → Datasets: both sections below the import, one column at a
    narrow width.
  - **Found live and fixed:**
    - the trees carried English words ("or", "(ignored)"), which are now gone; the text
      says it;
    - every site's name came twice ("Hugging Face — Hugging Face Datasets: …"); the link
      carries the name now;
    - the sections had no background over the animated one.
- **`cargo check`** accepts the capability.
