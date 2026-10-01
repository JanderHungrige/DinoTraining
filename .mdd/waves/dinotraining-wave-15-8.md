---
id: dinotraining-wave-15-8
title: "Wave 15.8: Models & Datasets — the entry point, dataset import with any layout, an own emblem"
initiative: dinotraining
initiative_version: 15
status: complete
depends_on: dinotraining-wave-15-7
demo_state: "The app and the download site carry a new emblem (a round coin with a mirrored T-rex skeleton, yellow on black, no text). The second tab is 'Models & Datasets' with three sub-tabs: Official Models (today's Admin page), Datasets (the Library's datasets plus an import), My Models (the Library's heads and fine-tuned models); the Library tab is gone and Start here and the README describe the new order. Pointing the import at a folder of images, a video, a COCO, YOLO, Pascal VOC or OpenLABEL export shows what was recognised, takes a description, and saves a dataset with its parameters (created, images or video, picture count, annotated count, classes, annotation types). The Datasets sub-tab explains how a downloaded dataset must be laid out, lists known dataset sites, and offers OSDaR23 (Deutsche Bahn) as an example in two forms: all sensors, or the RGB centre camera only."
created: 2026-10-01
hash: 423e924f
---

# Wave 15.8: Models & Datasets

**Jan's request (2026-10-01):**

- **The logo.** A Jurassic-Park-style coin with the T-rex skeleton, yellow-black and
  mirrored.
  - **Decided:** an own emblem in that style, **without text**. The Jurassic Park
    logo is Universal's trademark; the printables file is fan art of it.
- **"One thing is missing: a tab to use a downloaded dataset and make it a dataset for
  the tool."**
  - Admin/Models becomes **Models/Datasets**, right after Start here: "this is the
    actual entry point".
  - Three sub-tabs: **Official Models**, **Datasets**, **My Models**.
  - **Decided:** the Library tab goes into it. Its datasets go to *Datasets*, its
    heads and fine-tuned models to *My Models*.
  - **Decided:** *Official Models* is today's Admin page as it is, appearance
    included. Settings get their own place later, if more of them come.
- **Datasets sub-tab:**
  - the existing dataset management;
  - an import, like opening a folder in the other tabs: with or without annotations,
    with a description, the dataset's parameters saved automatically;
  - an explanation of how a downloaded dataset must be laid out to be importable, per
    annotation type;
  - known dataset sites, OSDaR23 (Deutsche Bahn) among them;
  - two buttons for OSDaR23 as an example: (A) the full set (several cameras, lidar),
    (B) only the RGB centre camera.
- **Cloud datasets** (S3 and similar, fetched in batches, annotations saved back) are
  **Wave 15.9**, after this one.

## What exists already (checked 2026-10-01)

- **COCO import** (doc 31): `POST /datasets/import/coco` and MCP
  `import_coco_dataset`. It reads Roboflow and Hugging Face exports and resolves
  classes by name. It is **not in the UI**.
- **OpenLABEL → COCO** (doc 49, OSDaR23):
  - `openlabel.py` and `openlabel_to_coco.py`;
  - a streamed download that keeps only `rgb_center/` and the labels, because the
    portal ignored Range requests;
  - track polylines excluded, signal boxes derived from quads.
- **Library tab** (doc 47): datasets, heads, fine-tuned models, export (doc 121),
  delete.
- **Admin tab:** model downloads, system, GPU (doc 128), token, appearance,
  distribution notice, head catalogue, starter set.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | app-emblem | docs/134-app-emblem.md | complete | — |
| 2 | models-datasets-tab | docs/135-models-datasets-tab.md | complete | — |
| 3 | dataset-import | docs/136-dataset-import.md | complete | models-datasets-tab |
| 4 | dataset-guide | docs/137-dataset-guide.md | complete | dataset-import |
| 5 | osdar23-example | docs/138-osdar23-example.md | complete | dataset-import |

### Feature notes

1. **app-emblem (134).**
   - One SVG source: a round coin, a T-rex skeleton facing the other way from the film
     logo, yellow (#f5c518 family) on black, no text. Drawn by hand as paths; nothing
     traced from the trademark.
   - Every icon Tauri needs, made from it (`tauri icon`): .icns, .ico, PNGs.
   - The app header, the download site's header and favicon, and the README.
2. **models-datasets-tab (135).**
   - The tab "Models & Datasets" ("Modelle & Datensätze"), second after Start here,
     with sub-tabs Official Models · Datasets · My Models.
   - Official Models is today's Admin page unchanged. Datasets and My Models are the
     Library's two halves; the Library tab goes.
   - The new tab order: Start here, Models & Datasets, Inspect, Studio, Prepare,
     Training, Inference, Generator, Connection.
   - Links that pointed at the Library or Admin follow (navigation requests, Start
     here, help texts, MCP guide).
   - Start here and the README describe the new entry point.
3. **dataset-import (136).**
   - "Import a dataset": pick a folder (or a video file), see what was recognised,
     name it, describe it, import.
   - **Detected:**
     - plain images or a video, without annotations;
     - COCO (boxes, polygons, RLE masks);
     - YOLO (boxes and segmentation polygons, with `data.yaml` or `classes.txt`);
     - Pascal VOC (boxes);
     - OpenLABEL / RailLabel (doc 49's reader).
     - Mixed or unknown: says what it found and what it expected.
   - **Saved with the dataset:** description, created (and imported from where),
     images or video, picture count, annotated pictures, classes, annotation types
     (boxes, masks, polygons). Shown in the list and in Inspect.
   - The existing importers grow behind one `POST /datasets/import` with a detect step
     (`POST /datasets/import/detect`); MCP gets the same.
4. **dataset-guide (137).**
   - In the Datasets sub-tab, folded: the folder layout per format, with a small tree
     each, and what "without annotations" means.
   - Known dataset sites: Hugging Face Datasets, Roboflow Universe, Kaggle, Open Images,
     COCO, and OSDaR23 / Digitale Schiene Deutschland.
5. **osdar23-example (138).**
   - Two buttons: (A) everything (all cameras, lidar, labels, ~841 MB) and (B) the RGB
     centre camera and its labels only, kept while streaming (doc 49's technique).
   - Both import into a dataset with its description and licence attribution.
   - **The portal now sits behind a bot check** (Anubis, seen 2026-10-01). If the app
     cannot fetch the file directly, the button opens the download page in the
     browser, and the import takes the downloaded ZIP (B keeps only `rgb_center` from
     it). Decided at build time by a real download, never by working around the check.

*(This wave is not complete until the demo state can be shown in the running app.)*
