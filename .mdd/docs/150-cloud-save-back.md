---
id: 150-cloud-save-back
title: Cloud Save-Back — A Linked Dataset's Annotations Exported Into Its Bucket, Never Over Someone Else's Newer Save
edition: DinoTraining
depends_on: [148-cloud-dataset-link, 143-export-targets, 144-auto-export]
relates: [142-annotation-export, 149-picture-fetch-cache]
source_files:
  - backend/app/datasets/exchange/cloud_export.py
  - backend/app/datasets/exchange/targets.py
  - backend/app/datasets/exchange/export.py
  - backend/app/cloud/errors.py
  - backend/app/cloud/linking.py
  - backend/app/api/v1/dataset_exchange.py
  - backend/app/i18n/de_cloud.py
  - apps/frontend/src/components/DatasetExport.tsx
  - apps/frontend/src/api/datasetExport.ts
routes:
  - POST /api/v1/datasets/{dataset_id}/export
  - GET /api/v1/datasets/{dataset_id}/export/target
models: [datasets, cloud_links]
test_files:
  - backend/tests/test_cloud_save_back.py
  - apps/frontend/src/components/DatasetExport.test.tsx
data_flow: writes-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [cloud, export, save-back, conflict, etag, annotations, s3, azure, gcs]
path: Cloud/Save Back
initiative: dinotraining
wave: dinotraining-wave-15-9
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**No real cloud provider was used:** the conditional writes were enforced by S3Mock (412 Precondition Failed), as AWS S3 does since 2024; Azure (ETag) and GCS (generation) use the same obstore call but were not exercised against the real services."
  - "A conflict is reported and both versions are kept; there is no side-by-side comparison in the app yet. Either version can be restored by linking or importing it."
security_read_sites: []
sister_projects: []
---

# 150 — Cloud Save-Back

## Purpose

- **Jan (2026-10-01):** "The annotated data should then also be saveable to a cloud
  storage."
- **A linked dataset's annotations go where its pictures are:** the export of doc 142, at
  doc 143's target, run by doc 144's button, closing and interval.

## "With the data" for a linked dataset

- **It is `<bucket>/<prefix>/dinotraining/`:** `dinotraining.json` and
  `annotations.coco.json`, as doc 142 writes into a folder.
  - The pictures are already in the bucket, so they are never copied.
  - The export's picture paths are the bucket keys (relative to the prefix), since the
    cache mirrors them. Linking that prefix again (doc 148) restores the dataset
    completely.
- **A newly linked dataset gets this target straight away.** It saves back by itself on
  closing (doc 144's default) and whenever "Export" is pressed. A folder can still be
  chosen instead.

## Never over someone else's newer save

- **Each file is written with a condition** (doc 147's `put_if`):
  - the first time, "only if it does not exist yet";
  - after that, "only if it is still the version I wrote last" (its ETag, kept with
    doc 143's export record).
- **If the bucket holds a newer one** (another person, another machine), nothing is
  overwritten:
  - this export goes **beside it**, into `dinotraining/conflicts/<time>/`;
  - the export reports the conflict and where both are;
  - nothing is lost, and either version can be restored by linking or importing it.
- **A dataset restored from an export in its bucket** (doc 148) starts from that export's
  ETags. Its first save-back is an update, not a false conflict.
- **Credentials that may not write** fail with that reason. The user can choose a local
  folder instead (doc 143).
  - The app does not probe a bucket with test writes: an object it did not need to
    write is noise in someone else's bucket.

## UI

- **The Export panel** (doc 143) offers "With the data (s3://bucket/prefix/dinotraining)"
  for a linked dataset; "Copy the pictures too" does not apply.
- **A conflict is shown as the export's answer:** where the newer save is, and where this
  one went.

## Found while building

- **A restore's baseline was recorded before the dataset's source was set.** The restored
  dataset therefore read as "changed" at once. The baseline is now taken after the last
  write.
- **`ExportConflict` is a `ValueError`.** The API catches it first and answers 409, not
  the 422 its parent class would get (CLAUDE.md: ordering).
- **The conflict message carried the provider's whole answer** (412, XML). It now says
  what matters: where the newer save is and where this one went. The details stay in the
  log.

## Verified (2026-10-01)

- **Backend (1982 tests, 5 new):**
  - **A linked dataset's target is its bucket by default:**
    - `s3://photos/dinotraining`, `linked`, no pictures to copy;
    - the export lands there with keys as picture paths;
    - an update of its own export is allowed.
  - **A colleague's newer save:**
    - theirs kept untouched;
    - ours in `conflicts/<time>/` with our change;
    - `ExportConflict`;
    - the API answers 409.
  - **A dataset restored from its bucket** updates it without a false conflict.
  - **Closing the app** (doc 144) saves a changed linked dataset back, and names a
    conflict as failed with the reason.
  - **A German reader** reads the conflict in German.
- **Frontend (1185 tests, 1 new):** a linked dataset's panel offers "With the data
  (s3://…)" and no "Copy the pictures too".
- **Live (German UI; the OSDaR23 sequence linked from S3Mock):**
  - **Export:** the panel offered "Bei den Daten (s3://photos/osdar/dinotraining)";
    "Jetzt exportieren" wrote both files ("Geschrieben nach s3://…: 10 Bilder · 300
    Objekte", "Exportiert vor 1 Sekunde").
  - **Conflict:**
    - a colleague overwrote `dinotraining.json` directly and one picture's split was
      changed;
    - "Jetzt exportieren" answered "Jemand anderes hat seit deinem letzten Export
      Annotationen nach s3://photos/osdar/dinotraining gespeichert. Nichts wurde
      überschrieben: Deine liegen unter …/conflicts/20261001T142250Z.";
    - the bucket: the colleague's file untouched, ours (split `val`, 300 boxes) in
      `conflicts/`.
