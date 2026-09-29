---
id: 73-generator-video-source
title: A Video as the Dataset Generator's Source
edition: DinoTraining
depends_on: [68-video-playback, 70-generator-action-bar, 69-remembered-entries]
relates: [22-mask-dataset-store, 29-generated-dataset-writer, 50-dataset-as-source]
source_files:
  - backend/app/ml/video/extract.py
  - backend/app/api/v1/video_extract.py
  - backend/app/api/v1/dataset_images.py
  - backend/app/api/v1/datasets.py
  - backend/app/api/v1/router.py
  - backend/app/datasets/schema.py
  - backend/app/datasets/migrations.py
  - backend/app/datasets/models.py
  - backend/app/datasets/images.py
  - backend/app/datasets/sequences.py
  - backend/app/datasets/store.py
  - backend/app/datasets/masks.py
  - apps/frontend/src/api/videoExtract.ts
  - apps/frontend/src/api/datasets.ts
  - apps/frontend/src/components/ImageSourceField.tsx
  - apps/frontend/src/components/VideoSourceFields.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/hooks/useGeneratorImages.ts
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/hooks/useSessionImages.ts
  - apps/frontend/src/lib/generatorSave.ts
  - apps/frontend/src/lib/imageSource.ts
  - apps/frontend/src/lib/persisted.ts
  - apps/frontend/src/lib/dialog.ts
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
routes:
  - POST /api/v1/video/extract
  - GET /api/v1/video/extract/{job_id}
  - DELETE /api/v1/video/extract/{job_id}
  - GET /api/v1/datasets/{dataset_id}/images (adds sequence, frame_index)
  - PUT /api/v1/datasets/{dataset_id}/images (accepts frame)
  - PUT /api/v1/datasets/{dataset_id}/images/masks (accepts frame)
models:
  - images.sequence (TEXT, nullable)
  - images.frame_index (INTEGER, nullable)
test_files:
  - backend/tests/test_video_extract.py
  - backend/tests/test_video_extract_api.py
  - backend/tests/test_migrations_v8.py
  - apps/frontend/src/api/videoExtract.test.ts
  - apps/frontend/src/components/VideoSourceFields.test.tsx
  - apps/frontend/src/hooks/useGeneratorSession.video.test.ts
  - apps/frontend/src/lib/persisted.test.ts
data_flow: mixed
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [dataset-generator, video, frame-sequence, pyav, migrations, sqlite, dataset-store]
path: Dataset Generator/Video Source
initiative: dinotraining
wave: dinotraining-wave-9
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Decoding is linear from frame 0, as in doc 68. A range that starts deep into a long video pays for decoding everything before it (seconds per minute of 1080p). Exact frames matter more here than speed, as they did for playback."
  - "The size estimate assumes 0.2 bytes per pixel (JPEG q92 over camera footage). Flat synthetic frames come out far smaller and noisy footage larger, which is why it says 'estimate'."
  - "Frames live in the dataset's directory and go when it is deleted. Two datasets built from the same video each hold their own copy."
  - "A folder source is recorded as a sequence too, in sorted order. For a folder of unrelated photos that makes a 'sequence' in Inspect (doc 74) which is really a slideshow. That is harmless, but worth knowing."
  - "Doc 68's path-safety section describes a resolve_user_path that does not exist; the extract route has the same local-app trust as doc 68's routes. Tracked as its own task."
security_read_sites:
  - backend/app/api/v1/video_extract.py:start_extract (source path from the request)
sister_projects: []
---

# 73 — A Video as the Dataset Generator's Source

## Purpose

Part of the Wave 9 request: *"have an option to play the just now annotated video"*, which
first needs a video to be something the Generator can annotate. Jan chose: **the Generator
takes video files directly**, not only folders of frames.

## Architecture

```
Generator setup: Images from ( ) A folder ( ) A dataset (•) A video file
  VideoSourceFields: path [Video…], From frame / Frames / Every Nth, and before the click:
     "1,000 frames at 30 fps · 1920×1080. Decodes 120 frames — about 50 MB (estimate)."
        │ Start
        ▼
useGeneratorImages ─ extractFrames() ─ POST /video/extract → poll GET → frames
   "Decoding frames into the dataset — 12 of 120…"
   frameOf(path): video → {sequence: video path, frame_index: the video's own frame no.}
                  folder → {sequence: folder, frame_index: sorted position}
                  dataset → null (positions already stored, and kept)
        ▼
session.save → saveReview(config, review, frameOf(path)) → PUT …/images {…, frame}
        ▼
images.sequence / images.frame_index   (schema v8)   ← what doc 74 plays back in order
```

**Why files.** The proposers, the store, the trainer and COCO export all work on image
paths. Decoding once into files is what lets a video be a source without teaching every
one of them a second input kind. The frames go under
`<dataset>/frames/<stem>-<sha8>/<stem>-f000123.jpg`, so they belong to the dataset they were
annotated for. The hash of the full path keeps two `run1.mp4` files apart, and the stem in
each filename keeps a copying dataset from colliding them.

## Business Rules

1. **One pass over the stream**, keeping every `stride`-th frame from `start`, `count` of
   them. Never a seek per frame, which would be quadratic, and never an approximate seek,
   which is doc 68's rule for why the frame named 40 must *be* frame 40.
2. **JPEG q92.** The source was lossy already.
3. **Re-extracting a range rewrites nothing.** Existing files are kept, so Change setup
   followed by Start costs a decode and no writes.
4. **The total is what the video can give**: `min(count, ceil((frames − start) / stride))`.
   A start past the last frame is a 422 that says so.
5. **Status codes:**
   - unknown dataset or missing file: 404;
   - a file that is not a readable video: 415, caught before the `ValueError` backstop,
     because `VideoReadError` is a `ValueError`;
   - a bad range or a non-video suffix: 422;
   - never a 500.
6. **A save records the frame's position**, and a save without one **keeps** what is stored
   (`COALESCE`). Re-reviewing a frame through the dataset-as-source path knows nothing of
   its video and must not erase it.
7. **A dataset that copies images does not copy its own frames again.** `store_image_file`
   skips a source already inside the dataset directory.
8. **Leaving the tab cancels the extraction on the server** (`DELETE`), so no decoder keeps
   running for a session that is gone.
9. **The source, including its range, is remembered** (doc 69; the guard checks the range).
   Only the Generator offers video (`allowVideo`). The Studio and Viewer refuse a video
   source with a stated reason rather than a folder listing of a file.

## Verified in the running app (2026-09-29)

A 60-frame, 10 fps, 640×640 clip made from the chess images, "every 2nd", 30 frames:

- **Before the click:** "60 frames at 10 fps · 640×640. Decodes 30 frames into the dataset
  — about 2 MB (estimate)."
- **Start:** 30 JPEGs were written to `…/<dataset>/frames/chess-walk-53997340/`, and the
  session opened at "1 / 30".
- **Auto-propose and three Nexts** gave three saves. `GET /datasets/{id}/images` returned
  `chess-walk-f000000.jpg 0`, `…f000002.jpg 2`, `…f000004.jpg 4`: the video's own frame
  numbers, with `sequence` set to the video's path.
- **Found by the running app, not by the tests** (bug 1 below).

## Bugs

- **2026-09-29 — the new columns never reached a real install.**
  - **Symptom:** "no such column: sequence" as a 500 on the image listing and on every
    save.
  - **Cause:** `run_migrations` returned early for a database already at `LATEST_VERSION`,
    and doc 73 had added `ADDED_COLUMNS` entries without moving it. Every test built a
    fresh database, where schema.py already has the columns, so all of them passed. This
    is doc 22's bug for the fourth time.
  - **Fix:** `LATEST_VERSION` 7 → 8, **and** the gate now also checks for missing added
    columns, a cheap `PRAGMA table_info`. The mechanism whose docstring says "it cannot be
    made stale by call order" no longer can be.
  - **Tests:** `test_migrations_v8.py` includes a database stamped latest but missing the
    columns.
