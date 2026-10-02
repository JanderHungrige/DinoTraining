---
id: 149-picture-fetch-cache
title: Picture Fetch and Cache — Linked Pictures Fetched When a Reader Needs Them, a Batch Ahead, Kept in a Bounded Cache, Usable Offline
edition: DinoTraining
depends_on: [148-cloud-dataset-link]
relates: [150-cloud-save-back, 11-training-job-runner]
source_files:
  - backend/app/cloud/pictures.py
  - backend/app/cloud/cache.py
  - backend/app/cloud/links.py
  - backend/app/ml/images.py
  - backend/app/ml/training/loop.py
  - backend/app/finetune/adapters/rfdetr.py
  - backend/app/finetune/adapters/sam2.py
  - backend/app/finetune/adapters/sam3.py
  - backend/app/finetune/runner.py
  - backend/app/ml/foundation/finetune.py
  - backend/app/ml/foundation/finetune_runner.py
  - backend/app/prep/augment_plan.py
  - backend/app/prep/duplicates.py
  - backend/app/prep/input_preview.py
  - backend/app/api/v1/annotate.py
  - backend/app/api/v1/cloud.py
  - backend/app/core/config.py
  - backend/app/ml/training/runner.py
  - backend/app/datasets/intake/profile.py
  - backend/app/i18n/de_cloud.py
  - apps/frontend/src/tabs/LibraryTab.tsx
  - apps/frontend/src/api/datasetImport.ts
  - apps/frontend/src/i18n/en/cloud.ts
  - apps/frontend/src/i18n/de/cloud.ts
  - backend/app/main.py
  - apps/frontend/src/api/cloud.ts
  - apps/frontend/src/components/CloudConnections.tsx
  - apps/frontend/src/components/CloudCache.tsx
routes:
  - GET /api/v1/cloud/cache
  - PUT /api/v1/cloud/cache
  - POST /api/v1/cloud/cache/clear
models: [cloud_links, images]
test_files:
  - backend/tests/test_cloud_cache.py
  - apps/frontend/src/components/CloudCache.test.tsx
data_flow: reads-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [cloud, cache, lru, prefetch, offline, training, studio]
path: Cloud/Fetch and Cache
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**A dataset bigger than the cache downloads again every epoch** (pictures cycle through it). Head training caches features on its first pass (doc 11), so this hits augmented training and fine-tuning; the cache's size is the remedy."
  - "**Training does not count its uncached pictures before it starts** when offline: it skips each with a warning. The dataset list says how many are cached beforehand."
  - "Videos in a bucket are not linked (decoding needs the whole file)."
security_read_sites: []
sister_projects: []
---

# 149 — Picture Fetch and Cache

## Purpose

- **Doc 148 links without downloading.** This doc makes a linked picture appear when
  something needs it: the Studio, Inspect, Prepare, training, fine-tuning.
- **"Retrieve images in batches as needed"** (Jan): a batch ahead, so the reader rarely
  waits.

## One call before every open: `ensure_local`

- **Every place that opens a picture calls `ensure_local(path)` first:**
  - `read_image`, which the Studio's canvas route, inference on a dataset and the
    Generator go through;
  - training's `load_image`;
  - the fine-tune adapters (RF-DETR, SAM 2, SAM 3) and the foundation fine-tune;
  - Prepare's augment preview, duplicate scan and input preview.
- **For an ordinary file it returns at once.** For a cache path whose file is missing, it
  downloads the key from its link's bucket, writes it atomically and returns the path.
- **One download per picture at a time.** A reader that asks for a picture already being
  fetched (by the prefetcher, say) waits for that fetch instead of starting a second.
- **When the bucket cannot be read** (offline, credentials revoked), the picture is
  *unavailable*:
  - a `FileNotFoundError` saying "not in the cache, and the bucket could not be read";
  - every reader already handles a missing picture: the Studio shows its message,
    training skips it with a warning.

## A batch ahead

- **The Studio:** serving a linked picture prefetches the next 8 of its dataset (by path,
  the Studio's order).
- **Training and fine-tuning:** the job hands every picture it will read to the
  prefetcher when it starts, which works through them while the job consumes them.
- **The prefetcher:** 8 downloads in parallel, never one already in the cache, and one
  queue shared by all.

## A bounded cache

- **`DINO_CLOUD_CACHE_GB`** (default **5**) bounds the pictures in all links' caches
  together. Annotation files do not count and are never evicted.
- **Least recently used first.** Reading a cached picture touches it; when a fetch takes
  the cache over its bound, the oldest pictures go until it is at 90 % of it.
- **A dataset bigger than the cache still trains:** pictures cycle through the cache.
  Every epoch then downloads again; the settings say how big the cache is.
- **`GET /cloud/cache`** answers the bound and its use, with each linked dataset's cached
  and total pictures. `PUT` changes the bound. `POST …/clear` removes every cached
  picture.

## Offline

- **A linked dataset keeps working from its cache.** The dataset list's line says how
  many of its pictures are cached ("7 of 10 pictures cached"), so it is clear what works
  offline.
- **Training offline** uses the cached pictures and warns about each one it skips.

## Clean-up at start

- **Links without a dataset are removed with their cache folders:** a "Check" never
  linked (doc 148) and a linked dataset since deleted.

## UI (Models & Datasets → Datasets → "Cloud storage")

- **"Picture cache: 1.2 GB of 5 GB":** the bound is editable; "Empty the cache" removes
  every cached picture.
- **A linked dataset's row** says how many of its pictures are cached.

## Found while building

- **The Studio's picture route was `async`.** A download inside it would have stopped the
  whole backend for its duration. It is a plain function now, run in FastAPI's thread
  pool.
- **A link kept the storage built from its connection's first settings.** After changing
  the endpoint or a secret, the linked dataset would have gone on with the old ones. A
  changed or removed connection now drops its links' storages.

## Verified (2026-10-01)

- **Backend (1977 tests, 9 new):**
  - **Readers:** `read_image` (the Studio, inference, the Generator) and training's
    `load_image` fetch first; nothing is fetched that nobody asked for.
  - **One download for five concurrent readers.**
  - **An unreachable bucket:**
    - a cached picture still served;
    - an uncached one unavailable "not in the cache, and photos could not be read";
    - training skips it;
    - the Studio's route answers 404 with the reason, in German for a German reader.
  - **The bound:** the least recently used picture goes (a re-read one stays), and the
    use stays under the bound.
  - **Prefetching:**
    - the Studio's next pictures by path;
    - a list prefetch skips the cached ones.
  - **Clean-up:** a link without a dataset and its folder are removed; the linked one
    stays.
  - **The API:** bound and use with each dataset's cached count, the bound written to
    `.env`, the cache emptied, 0 GB refused.
  - **A changed connection** reaches its linked datasets at once.
- **Frontend (1184 tests, 2 new):**
  - "1.5 of 5 GB used";
  - the bound changed on leaving the field;
  - "Empty the cache" (disabled when empty);
  - a size that is not positive ignored;
  - German decimals ("1,5 von 5 GB").
- **Live (German UI, the OSDaR23 sequence linked from S3Mock):**
  - **The backend's start** removed the one link a "Check" had left without a dataset
    ("Removed 1 cloud links without a dataset").
  - **One picture through the Studio's route:**
    - 200, 5.6 MB in 0.25 s;
    - the following 8 prefetched: 9 of 10 cached, 54 MB.
  - **The connection pointed at a dead endpoint:**
    - the uncached picture answered 404 in 0.3 s with "…could not be read: The storage
      could not be reached…";
    - a cached one still 200;
    - the endpoint was put back afterwards.
  - **The dataset's line:** "10 Bilder · 10 annotiert · … · 9 von 10 im Cache aus
    s3://photos/osdar".
  - **Cloud storage:** "Bild-Cache: 0,05 von 5 GB belegt…".
