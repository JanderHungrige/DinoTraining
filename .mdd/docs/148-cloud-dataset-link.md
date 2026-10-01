---
id: 148-cloud-dataset-link
title: Cloud Dataset Link — A Bucket's Dataset Detected and Imported from Its Listing and Annotation Files, Without Downloading the Pictures
edition: DinoTraining
depends_on: [147-cloud-connection, 136-dataset-import]
relates: [149-picture-fetch-cache, 150-cloud-save-back, 142-annotation-export]
source_files:
  - backend/app/cloud/links.py
  - backend/app/cloud/linking.py
  - backend/app/cloud/storage.py
  - backend/app/datasets/intake/voc.py
  - backend/app/datasets/intake/walk.py
  - backend/app/datasets/exchange/restore.py
  - apps/frontend/src/components/CloudConnections.tsx
  - apps/frontend/src/components/DatasetImport.tsx
  - backend/app/cloud/pictures.py
  - backend/app/cloud/remote_listing.py
  - backend/app/datasets/intake/detect.py
  - backend/app/datasets/intake/importer.py
  - backend/app/datasets/intake/documents.py
  - backend/app/datasets/intake/yolo.py
  - backend/app/datasets/coco_import.py
  - backend/app/datasets/intake/jobs.py
  - backend/app/api/v1/cloud_links.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/cloud.ts
  - apps/frontend/src/components/CloudLink.tsx
  - apps/frontend/src/tabs/ModelsTab.tsx
  - apps/frontend/src/i18n/en/cloud.ts
  - apps/frontend/src/i18n/de/cloud.ts
routes:
  - POST /api/v1/cloud/links/detect
  - POST /api/v1/cloud/links
models: [cloud_links, datasets, images]
test_files:
  - backend/tests/test_cloud_links.py
  - backend/tests/test_intake_detect.py
  - apps/frontend/src/components/CloudLink.test.tsx
data_flow: writes-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [cloud, s3, azure, gcs, datasets, import, link, cache]
path: Cloud/Link
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**Each 'Check' creates a link and its cache folder**; one that is never linked stays until doc 149's cleanup removes links without a dataset."
  - "**Detection runs in the request**, as doc 136's: a bucket of tens of thousands of YOLO label files makes 'Check' take a while (16 files in parallel). A progress bar for detection would need it to become a job too."
  - "MCP's `link_cloud_dataset` is not built yet; the API is complete."
security_read_sites:
  - backend/app/cloud/remote_listing.py (bucket keys become local cache paths; they must stay inside the link's cache folder)
sister_projects: []
---

# 148 — Cloud Dataset Link

## Purpose

- **Jan (2026-10-01):** "do not download the whole dataset, but give the user an option to
  connect to the cloud set and retrieve images in batches as needed".
- **This doc links:** the dataset appears in the app with its annotations and
  parameters, and no picture is downloaded. Fetching pictures when they are needed is
  doc 149.

## One idea: a cloud picture has a local path from the start

- **Each link gets a cache folder:** `<data>/cloud/<link id>/`.
- **A picture's path in the database is where it *will* be:** `<cache>/<its key>`.
  - Every reader of the app opens paths as today.
  - Doc 149 makes "open" fetch the file first when it is not there yet.
  - The database, the Studio, training and the exports need no notion of a bucket.
- **Keys become paths only inside the cache folder.** A key with `..` or an absolute path
  is refused (as doc 142's restore).
- **`cloud_links`**: a new table with `id`, `connection_id`, `bucket`, `prefix`,
  `cache_root`, `dataset_id` (set once imported) and `linked_at`. It is how a cache path
  is traced back to its bucket key.

## Detection without the pictures

- **The bucket is listed in pages** (doc 147's `list`).
  - Keys are sorted into pictures, videos and annotation files, as doc 136's `walk`
    does.
  - At most 300 000 keys (doc 136's limit), refused beyond.
- **Only the annotation files are downloaded** into the cache folder: `.json`, `.txt`,
  `.xml`, `.yaml`.
  - YOLO's text files are many and small, so they are fetched in parallel.
- **Doc 136's detection then runs on that listing**, unchanged: the same summary, the
  same formats, the same notes.
- **A dataset exported by this app into the bucket** (doc 150) is recognised as such and
  restored completely.

## Import without the pictures

- **Doc 136's import, with three places taught about cloud pictures** (`pictures.py`):
  - **"does it exist"** (COCO's check): a cache path is there if its key was listed;
  - **its size, for formats that do not record it** (YOLO, plain pictures, OpenLABEL):
    read from the **first 64 KB** of the picture (a ranged read). PNG and JPEG keep their
    size there. Only if that is not enough is the whole picture read;
  - nothing is copied ("copy pictures" does not apply to a link).
- **The dataset's source** is `s3://bucket/prefix` (or `azure://`, `gs://`), and its
  description says which connection.
- **Runs as doc 136's background job,** with progress (listing, annotation files, sizes,
  import).

## API

- **`POST /cloud/links/detect`** `{connection_id, bucket, prefix}` → doc 136's
  `Detection`, plus the `link_id` to import with.
- **`POST /cloud/links`** `{link_id, name, description}` → doc 136's import job.
  - Its progress is read at `/datasets/import/jobs/{id}`.
- **A detection that is never imported** leaves only its annotation files in the cache.
  They are removed with the next start's cache cleanup (doc 149).

## UI (Models & Datasets → Datasets, "Link a cloud dataset")

- **Beside "Import a dataset":** the connection (from doc 147's list), the bucket, the
  prefix, then "Check".
  - It shows doc 136's summary, with name and description, then "Link".
  - Without a connection it says where to add one.

## Not here

- **Video files in a bucket:** listed, but not linked (decoding needs the whole file).
  The summary says so.
- **MCP:** `link_cloud_dataset(connection_id, bucket, prefix, name)` mirrors the two
  calls (planned in doc 147).

## Found while building

- **YOLO and Pascal VOC looked for each picture with `is_file()`.** From a bucket, every
  label lost its picture and the import failed ("no usable categories"). Both now ask
  `picture_exists`. A test caught it.
- **Doc 136's OpenLABEL detection over-counted**, locally too. OSDaR23's "RGB centre
  only" promised 90 pictures (the labels name nine cameras) and imported 10.
  - Pictures that cannot be opened are now dropped in the detection, with their
    annotations: the summary says what will arrive.
- **A bucket error during the import is not "no such picture".**
  - It fails the import instead of silently skipping pictures.
  - A key that was not listed is a `FileNotFoundError`, as a missing local file is.
- **`obstore` refuses keys with `..` itself.** The cache path refuses them again, in case
  a provider ever hands one over.
- **A new connection** is offered in "Link a cloud dataset" at once (the section re-reads
  when "Cloud storage" changes).

## Verified (2026-10-01)

- **Backend (1969 tests, 8 new):**
  - **COCO from a bucket:**
    - 4 pictures, 3 annotated, 2 masks;
    - **no picture in the cache**;
    - source `s3://photos`;
    - the link knows its dataset.
  - **YOLO, plain pictures and VOC:** sizes from the header, none downloaded.
  - **A bucket error** fails the import.
  - **A key leaving the cache** is refused.
  - **An export in the bucket** (doc 142) is detected as `dinotraining` and restored,
    with no picture downloaded.
  - **The helpers:** `picture_exists` / `picture_size` / `ensure_local` for a cache path
    and an ordinary one.
  - **The API:** detect, link as a job, 404s.
  - **The OpenLABEL count regression.**
- **Frontend (1182 tests, 3 new):**
  - the first connection by default;
  - check, summary, link, progress, re-read;
  - another connection chosen;
  - a refusal shown;
  - no connection → where to add one (German).
- **Live (German UI, S3Mock in Docker, the real OSDaR23 RGB-centre sequence uploaded to
  `photos/osdar`):**
  - "Prüfen" in 1.4 s: "Gefunden: OpenLABEL (OSDaR23) · 10 Bilder · 10 annotiert · 300
    Objekte · 6 Klassen";
  - "Verknüpfen": "10 Bilder · 10 annotiert";
  - **in the database:** source `s3://photos/osdar`, 10 pictures at 2464×1600 (read
    from each PNG's first 64 KB), 300 boxes, as the local import;
  - **the cache:** only `3_fire_site_3.4_labels.json` (7.6 MB), **0 PNGs**.
  - The linked dataset is kept for doc 149's checks.
