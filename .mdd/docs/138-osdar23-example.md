---
id: 138-osdar23-example
title: OSDaR23 Example — One Click Downloads a Real Rail Sequence, Everything or the RGB Centre Camera Only
edition: DinoTraining
depends_on: [136-dataset-import, 49-osdar23-rail]
relates: [137-dataset-guide]
source_files:
  - backend/app/datasets/examples/zipstream.py
  - backend/app/datasets/examples/catalogue.py
  - backend/app/datasets/examples/fetch.py
  - backend/app/datasets/intake/jobs.py
  - backend/app/datasets/intake/documents.py
  - backend/app/datasets/intake/detect.py
  - backend/app/api/v1/dataset_examples.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/datasetImport.ts
  - apps/frontend/src/components/ExampleDataset.tsx
  - apps/frontend/src/components/DatasetImport.tsx
  - apps/frontend/src/tabs/ModelsTab.tsx
  - apps/frontend/src/hooks/useImportJob.ts
  - apps/frontend/src/i18n/en/datasets.ts
  - apps/frontend/src/i18n/de/datasets.ts
  - apps/frontend/src/i18n/en/admin.ts
  - apps/frontend/src/i18n/de/admin.ts
routes:
  - GET /api/v1/datasets/examples
  - POST /api/v1/datasets/examples/{example_id}/import
models: [datasets, images, boxes]
test_files:
  - backend/tests/test_zipstream.py
  - backend/tests/test_dataset_examples.py
  - apps/frontend/src/components/ExampleDataset.test.tsx
data_flow: writes-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [datasets, osdar23, openlabel, example, download, zip, streaming, licence]
path: Datasets/Example
initiative: dinotraining
wave: dinotraining-wave-15-8
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**The example is ten moments.** Sequence 3_fire_site_3.4 has 10 frames: 10 pictures in B, 90 in A (nine cameras). It is a demonstration of the loop, not enough to train a useful detector; doc 49's sequence (98 frames, 9.84 GB) is the one for that."
  - "**B still transfers the whole archive** (764 MB): the server ignores Range requests, so B saves disk (61 MB kept), not bandwidth."
  - "**A running download cannot be cancelled** from the UI; closing the app ends it, and the next try replaces the `.part` folder."
  - "The dataset's name and description are English in both languages: they are data, written once at import."
security_read_sites:
  - backend/app/datasets/examples/zipstream.py (member names from a downloaded archive become file paths; absolute names and '..' are refused)
sister_projects: []
---

# 138 — OSDaR23 Example

## Purpose

- **Jan (2026-10-01):** "two download buttons for an example dataset which downloads
  A) the full set (several cameras, lidar, 841 MB) or B) the set but only keeps the RGB
  center camera", for the OSDaR23 resource he linked.
- **A real annotated dataset in one click**, so a new user can go straight to Prepare,
  Training and Inference without hunting for data.

## The resource (read 2026-10-01 through the portal's CKAN API)

- **Sequence `3_fire_site_3.4`:**
  - the resource Jan linked (`068947d5-…`);
  - its download is `https://download.data.fid-move.de/dzsf/osdar23/3_fire_site_3.4.zip`,
    with **763 518 017 bytes** (`content-length`; the page's "841 MB" is not what the
    server sends).
- **Licence, in two parts:**
  - The portal's package `license_id` is **CC BY-SA 3.0 DE**.
  - The archive's own `license.md` is more precise: the **sensor data** (pictures,
    lidar, radar) are CC BY-SA 3.0 DE, and the **annotation files are CC0 1.0** (found
    live, after the first download).
  - The card and the dataset's description name both.
  - **Attribution:** DZSF (German Centre for Rail Traffic Research at the Federal Railway
    Authority), Digitale Schiene Deutschland / DB Netz AG, and FusionSystems GmbH;
    doi:10.57806/9mv146r0.
  - **ShareAlike** (for the pictures): the dataset's description says so, and the app
    shows it under the buttons.
- **Reachable without the bot check.** The plan feared it (Anubis on the portal's web
  pages, seen 2026-10-01).
  - The download host and the API answer an honest client (`User-Agent:
    DinoTraining/<version>`) with 200 and the file. Anubis challenges browsers, not
    clients that say what they are.
  - Nothing is disguised: no browser user agent, no solved challenge.
  - If the host ever refuses the app, the job fails with the reason and the portal link,
    and the guide (doc 137) still explains how to download and import by hand.

## One pass over the network, nothing but what is kept on disk (`examples/zipstream.py`)

- **Doc 49's technique, now in the app:** the ZIP is read sequentially by its local file
  headers while it downloads.
  - The archive stores every member's sizes in its local header (flag 0, deflate or
    stored). Checked against the real file's first 22 entries.
  - Each member is decompressed to disk or skipped as it passes; the ZIP itself is never
    written.
  - The server ignores Range requests (doc 49), so this is the only way B can avoid
    transferring everything. B still transfers the whole archive; what it saves is disk.
- **A (everything):** every sensor is kept: nine cameras, lidar, radar and the IMU logs.
  The readme's preview pictures (`readme_img/`) are not, because the import would take
  them for data.
- **B (RGB centre):** only `rgb_center/` and the `*_labels.json` are kept.
- **Refused, with the reason:**
  - a member with a data descriptor (sizes after the data): it cannot be skipped without
    decompressing it;
  - a ZIP64 size;
  - an encrypted member;
  - a name that is absolute or contains `..` (zip-slip).
- **Written to `<data>/examples/<sequence>-<variant>.part/`, renamed when complete.**
  - A broken download leaves no half folder that looks finished.
  - A finished folder is reused: importing B a second time does not download again.
- **Space is checked first:** the archive's size (A), or a tenth of it (B), plus 1 GB.

## Then the import (doc 136)

- The finished folder goes through `run_import` as any OpenLABEL folder:
  - in place, not copied (it already lives in the app's data folder);
  - named "OSDaR23 · 3_fire_site_3.4 · <variant>";
  - its description carries the sequence, the licence and the attribution.
- **One job, two phases.** `ImportJob.phase` is `download`, then `import`. Progress is in
  MB while downloading and in pictures while importing.
- **A second click joins the running job** of the same example and variant, instead of
  writing into the same `.part` folder twice.
- **The example list names a running job** (`running_job`). The card follows it again
  when it is opened later: another sub-tab, or a reload. Without this, the progress
  vanished while the download went on (found live).
- **A camera without one annotation is not an annotated document** (`documents.py`).
  - Doc 49 measured that OSDaR23's side cameras carry no boxes at all. Imported as
    "annotated, empty", every side-camera frame would train as pure background, with the
    people and signals in it unlabelled.
  - Such a camera's pictures now arrive **never saved** (doc 136), so they are there to
    annotate and out of training until saved.
  - This matters for A: it has nine cameras. In this sequence all nine carry
    annotations (the side cameras' are closed signal quads), so all 90 pictures are
    annotated; in doc 49's sequence they did not.
- **An OpenLABEL folder's pictures are its cameras' frames only** (`camera_pictures`).
  OSDaR23 ships its radar as PNG renderings. Before this, A imported them as 10 more
  "pictures" (found live: 100 pictures instead of 90).

## UI (Models & Datasets → Datasets)

- **A card "Example dataset: OSDaR23 (rail)"** between the import and the guide.
  - A short description.
  - Two buttons:
    - "Everything: all cameras, lidar, radar";
    - "RGB centre camera only".
    - Both say the download size.
  - The licence line, with a link to the portal page.
- **While running:** the same progress bar as the import, worded per phase.
- **When done:** the list re-reads itself, as after an import.

## Not here

- **Cancelling a running download:** not built. It runs for minutes, and closing the app
  ends it; the `.part` folder is replaced on the next try.
- **Other OSDaR23 sequences:** the catalogue has one entry; adding a sequence is one
  entry, if Jan wants more.
- **An MCP tool:** not built; `import_dataset` on the downloaded folder covers an agent.

## Verified (2026-10-01)

- **Backend (1925 tests, 12 new):**
  - the streaming unpacker:
    - only the wanted members, deflated and stored, at chunk sizes of 3 bytes to 1 MB;
    - it stops at the central directory;
    - refused: sizes after the data, a name leaving the folder (`..`, absolute,
      a drive letter);
    - "ended in the middle", a damaged member (CRC), and an HTML page instead of a ZIP;
  - the variants keep what Jan asked for, the readme pictures excluded;
  - a finished folder is reused (no second download); a broken download leaves no
    folder;
  - a camera without annotations and the radar renderings;
  - the whole job (download phase, then import), with a second click joining it;
  - the API: the list (with `running_job`), 202, 404, and 422 for an unknown variant.
- **Frontend (1150 tests, 5 new):**
  - both variants with the size and what they keep;
  - the download followed into the import, then the list re-read;
  - a running download picked up again;
  - "already downloaded";
  - a refusal shown;
  - German.
- **Live, in the running app (German), against the real portal:**
  - **B:**
    - streamed the 764 MB archive and kept 61 MB (`rgb_center/`, 10 pictures, and
      the labels);
    - imported: "10 Bilder · 10 annotiert · 6 Klassen" (catenary_pole, flame,
      person, signal, signal_pole, train).
  - **A:**
    - kept 865 MB (nine cameras, lidar, radar, IMU, `license.md`, `readme.md`);
    - switched to Official Models and back mid-download: the card came back showing
      "Wird geladen … 116 von 764 MB" with both buttons locked.
  - **Found live and fixed:**
    - the radar renderings imported as pictures;
    - the two-part licence;
    - the progress lost on leaving the sub-tab;
    - "Bahn" twice in the German lead;
    - why 764 MB for 10 moments (the card now says).
  - **After the fixes, both re-imported from the downloaded folders without
    downloading:**
    - A: "90 Bilder · 90 annotiert · 7 Klassen";
    - B: "10 Bilder · 10 annotiert".
  - **Left in the app for Jan to try:**
    - both example datasets;
    - their folders in `<data>/examples/`.
