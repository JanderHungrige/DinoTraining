---
id: dinotraining-wave-15-9
title: "Wave 15.9: Keep your work, and cloud datasets — exports where the data lives, S3-compatible datasets fetched in batches"
initiative: dinotraining
initiative_version: 16
status: planned
depends_on: dinotraining-wave-15-8
demo_state: "A user's annotations and trained models never live only inside the app. Each dataset exports its annotations to a remembered place: 'with the data' (beside its pictures, or into its bucket) or a chosen folder. The export runs on a button, on closing the app and, if switched on, every n minutes, only for what changed; trained models export to their own remembered folder. Importing an exported folder restores the dataset completely. The app says plainly that uninstalling removes what is inside it and that exports stay. A dataset in an S3 bucket (or MinIO, Wasabi, Cloudflare R2) is linked instead of downloaded. The app lists and detects it like a local import, fetches pictures in batches as the Studio, Inspect, training and the Generator need them, keeps a bounded local cache, works offline from that cache, and saves annotations back to the bucket through the same export, refusing to overwrite someone else's newer save."
created: 2026-10-01
hash: e5018462
---

# Wave 15.9: Keep your work, and cloud datasets

**Jan (2026-10-01):**

- **Cloud datasets:**
  - "For large datasets that are saved in an S3, or somewhere else, we do not download
    the whole dataset, but give the user an option to connect to the cloud set and
    retrieve images in batches as needed."
  - "The annotated data should then also be saveable to a cloud storage."
- **Keeping work across an uninstall** (from the Microsoft Store discussion, Wave 15.10):
  - "A warning that with uninstalling all data disappears but can be exported."
  - "A checkbox with auto export of model / annotations on app closing or every n
    minutes."
  - "Work in the database to keep the speed and export into the data folder with an
    export button, when closing the application, or every n minutes."
  - "The export folder has to be asked from the user. Have 'save with the data' as an
    easy option for the annotations. Also remember the last saved location."
- **Order:** this wave first, then the Microsoft Store (15.10). The EXE build stays.

## Why one wave

- **Saving annotations back to a bucket is an export with a cloud destination.** The
  export target (a folder, the data's own place, a bucket prefix) is built once and used
  by both halves.
- **15.10 needs the export to exist.** Under MSIX, Windows deletes the app's own folders
  on uninstall, with no uninstaller page to warn from. The warning and the export must
  already be in the app.

## What exists already (checked 2026-10-01)

- **The annotations live in SQLite** in the app's data folder. The pictures are
  referenced in place (doc 136's default) or copied into the data folder.
- **`POST /datasets/{id}/export/coco`** writes `annotations.coco.json` into the app's
  own dataset folder:
  - never-saved pictures are left out (doc 136);
  - the guideline is included (doc 109).
- **Doc 136's import** reads a COCO folder back, but COCO carries nothing of the app's
  own:
  - phrases and variants (doc 103);
  - per-picture checks and "absent" marks;
  - hard negatives;
  - never-saved status;
  - masks' provenance.
- **Doc 121 exports a trained model** as a zip with its model card. Doc 122 adds ONNX.
- **The shell already runs code on quitting** (`RunEvent::ExitRequested`): it stops the
  backend.
- **Credentials:** `.env` beside the data, written by the settings API, never returned or
  logged (`HF_TOKEN`, doc 24). CLAUDE.md puts cloud credentials there too.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | annotation-export | docs/142-annotation-export.md | planned | — |
| 2 | export-targets | docs/143-export-targets.md | planned | annotation-export |
| 3 | auto-export | docs/144-auto-export.md | planned | export-targets |
| 4 | model-export-target | docs/145-model-export-target.md | planned | export-targets |
| 5 | uninstall-notice | docs/146-uninstall-notice.md | planned | auto-export, model-export-target |
| 6 | cloud-connection | docs/147-cloud-connection.md | planned | — |
| 7 | cloud-dataset-link | docs/148-cloud-dataset-link.md | planned | cloud-connection |
| 8 | picture-fetch-cache | docs/149-picture-fetch-cache.md | planned | cloud-dataset-link |
| 9 | cloud-save-back | docs/150-cloud-save-back.md | planned | export-targets, cloud-dataset-link |

### Feature notes

1. **annotation-export (142): a full export, and a full restore.**
   - **Two files in `<target>/dinotraining/`:**
     - `annotations.coco.json` (what other tools read: boxes, masks, classes; doc 136
       reads it back);
     - `dinotraining.json`, everything COCO cannot carry: phrases and variants, checks
       and "absent" marks, hard negatives, never-saved pictures, provenance, the
       guideline, the dataset's description and parameters, and the export's own time
       and app version.
   - **Paths are relative to the pictures' folder**, so a moved folder (or another
     machine) still matches.
   - **Restore = import.** Doc 136's detection recognises `dinotraining.json` and
     restores the dataset completely, instead of reading it as plain COCO.
   - **Written atomically** (a temporary file, then a rename): an export interrupted by
     closing the app never leaves half a file.
   - The database stays the working copy, for speed (Jan).
2. **export-targets (143): where it goes, remembered.**
   - **Per dataset**, one of:
     - **"With the data"**: `<the pictures' folder>/dinotraining/`, offered when the
       pictures live outside the app (doc 136's in-place default), and the bucket prefix
       for a cloud dataset (feature 9);
     - **a chosen folder**, from the native dialog.
   - **Remembered per dataset.** A new dataset's dialog opens at the last place used.
   - **A dataset whose pictures live inside the app** (copied, generated, the OSDaR23
     example) has no "with the data". Its first export asks for a folder, and offers to
     write the pictures too, so the export is complete without the app.
   - **UI:** "Export annotations" on each dataset in Models & Datasets → Datasets. The
     row shows the target and the last export ("exported 3 minutes ago").
3. **auto-export (144): on closing, and every n minutes.**
   - **Settings:**
     - "Export annotations when closing the app" (default **on**);
     - "…every [10] minutes" (default **off**).
   - **Only what changed** since the dataset's last export, judged from the database's
     newest save. A dataset without a target is skipped, and the app reminds the user
     to give it one.
   - **On closing,** the shell asks the backend to finish exports before stopping it,
     with a time limit, so a stuck disk cannot hang the quit. What did not finish is
     logged and named at the next start.
   - **Interval exports** run in the background job runner. They never block the
     Studio.
4. **model-export-target (145): trained models, the same way.**
   - **Doc 121's "Export"** remembers its folder. The dialog opens there next time.
   - **Optional:** "Export each trained model when its training finishes" into that
     folder (default off).
5. **uninstall-notice (146): say it before it matters.**
   - **In the app,** where the Datasets and My Models lists are: "Everything inside
     DinoTraining is removed when you uninstall it. Exported annotations and models
     stay where you saved them."
     - With the state: which datasets have no export target, or unexported changes.
     - With a button to export everything now.
   - **The EXE uninstaller** (doc 132) points to it beside its "delete the application
     data" checkbox.
   - **Under MSIX (15.10)** there is no uninstaller to warn from, so this in-app notice
     is the only one.
6. **cloud-connection (147): an S3-compatible account.**
   - **Fields:**
     - an endpoint (empty for AWS) and a region;
     - an access key and a secret;
     - a name.
   - **Covers** AWS S3, MinIO, Wasabi, Cloudflare R2 and Ceph: one client, one protocol.
     Azure Blob and Google Cloud Storage only if asked for.
   - **Secrets go into `.env`**, as with `HF_TOKEN` (CLAUDE.md). They are never returned,
     logged or kept in the database. The database keeps only the connection's name and
     endpoint.
   - **"Test connection"** lists one key and says plainly what failed: DNS, credentials,
     permission, region.
   - **API:** `/api/v1/cloud/connections`. **MCP** mirrors it without ever exposing the
     secret.
7. **cloud-dataset-link (148): link, do not download.**
   - **"Link a cloud dataset"** beside doc 136's import: connection, bucket, prefix.
   - **Detection runs on the listing and the annotation files only** (doc 136's intake,
     fed a remote listing): the same summary, the same formats. A bucket of a million
     pictures is listed in pages, never downloaded.
   - **The dataset row records its remote source.** Its pictures are referenced by key,
     not path.
   - **Restoring** from a bucket that holds a `dinotraining/` export restores everything
     (feature 1).
8. **picture-fetch-cache (149): pictures when needed.**
   - **One resolver** turns a picture reference into a local file for every reader: the
     Studio, Inspect, Prepare, training, inference on a dataset, the Generator and the
     exports.
   - **Remote pictures** are fetched on demand, a batch ahead of where the user or the
     job is (the Studio's next pictures, the training loader's next batch).
   - **A size-bounded LRU cache on disk.** The bound is a setting (default 5 GB); the
     cache is cleared from the same place.
   - **Training** streams through the cache instead of copying the set first, and works
     with doc 11's feature cache: a picture whose features are cached is not fetched
     again.
   - **Offline:** a linked dataset works from its cache and says how many pictures are
     not cached, instead of failing in the middle of a job.
9. **cloud-save-back (150): annotations back to the bucket.**
   - **"With the data"** for a cloud dataset is `<prefix>/dinotraining/` in its bucket.
     The export button, closing the app and the interval (features 2–3) all write there.
   - **No silent overwrite.** The export remembers the version (ETag) it last wrote.
     - If the bucket holds a newer one (another person, another machine), it stops and
       says so: keep theirs, keep mine (as a copy beside it), or compare.
     - Conditional writes where the store supports them (`If-Match`). Otherwise a
       check just before the write, with the remaining race stated.
   - **Read-only credentials** are detected at link time. Save-back is then offered to a
     local folder instead.

## Decisions taken in planning (Jan to confirm)

- **D1, the export format:** COCO for other tools plus `dinotraining.json` for
  everything else. Importing the folder restores the dataset completely.
- **D2, datasets inside the app:** their first export asks for a folder and offers to
  write the pictures too. "With the data" is not offered, because there the data is the
  app.
- **D3, defaults:** export on closing **on**; every 10 minutes **off**; models after
  training **off**.
- **D4, credentials** in `.env`, like the HF token, and not in the OS keychain:
  - it is what CLAUDE.md asks for;
  - one mechanism to protect;
  - the keychain could follow later.
- **D5, stores:** S3-compatible only.

## Open research

- **The S3 client for the bundled runtime:** `boto3` (large, ubiquitous) or `obstore`
  (small, Rust-based, async) or `minio`. Measure the runtime size each adds, and check
  `If-Match` support on R2 and MinIO.
- **The training loader's prefetch** with doc 11's feature cache: does a cached feature
  ever need its picture again (augmentation does)?
- **How long the shell may wait on quit** before Windows or macOS treats the app as hung.

*(This wave is not complete until the demo state can be shown in the running app.)*
