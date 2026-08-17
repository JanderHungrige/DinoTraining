---
id: 03-dataset-store
title: Dataset Store — On-disk Format, SQLite Index & Counters
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-1
wave_status: complete
depends_on: [01-app-shell]
relates: [02-model-manager]
source_files:
  - backend/app/datasets/__init__.py
  - backend/app/datasets/db.py
  - backend/app/datasets/models.py
  - backend/app/datasets/store.py
  - backend/app/datasets/coco.py
  - backend/app/api/v1/datasets.py
routes:
  - POST /api/v1/datasets
  - GET /api/v1/datasets
  - GET /api/v1/datasets/{dataset_id}
  - DELETE /api/v1/datasets/{dataset_id}
  - PUT /api/v1/datasets/{dataset_id}/images
  - GET /api/v1/datasets/{dataset_id}/counts
  - POST /api/v1/datasets/{dataset_id}/export/coco
models:
  - datasets
  - images
  - boxes
test_files:
  - backend/tests/test_db.py
  - backend/tests/test_store.py
  - backend/tests/test_coco.py
  - backend/tests/test_datasets_api.py
data_flow: greenfield
last_synced: 2026-08-17
status: complete
phase: all
mdd_version: 11
tags: [sqlite, coco, dataset, annotations, provenance, counters, persistence]
path: Platform/Datasets
integration_contracts:
  - function: get_connection()
    when: any backend code touching SQLite — never open sqlite3.connect directly
    applies_to: every persistence-touching feature in this initiative
  - function: DatasetStore.replace_image_boxes(dataset_id, image_path, boxes, prompt)
    when: saving annotations for one image — the only sanctioned write path
    applies_to: annotation-workflow, dataset-generator
satisfies_contracts:
  - from: 01-app-shell
    function: get_settings()
    when: any backend module needing configuration
    status: done
    verified_at: "backend/app/datasets/db.py:70 — data_root(); no module reads os.environ"
  - from: 02-model-manager
    function: ensure_within(root, candidate)
    when: any code turning external input into a filesystem path
    status: done
    verified_at: "backend/app/datasets/store.py:42 (dataset_dir), :208 (image copy destination)"
security_read_sites: []
known_issues:
  - "DatasetStore.list_all() runs one counts() query per dataset (N+1). Fine for the tens of datasets Wave 1 expects; fold into a single GROUP BY if the list ever gets slow."
  - "The SQLite index cannot yet be rebuilt from dataset.json — the manifest is the stated source of truth but no rebuild path exists. Write one before Wave 5 ships to users."
  - "copy_images with two source files of the same basename collides in images/; the second is silently skipped as already-present. Hash or namespace the filename when the dataset generator (Wave 4) starts pulling from many folders." 
sister_projects: []
---

# 03 — Dataset Store — On-disk Format, SQLite Index & Counters

## Purpose

Persists annotations in a form the Wave 2 trainer can consume directly, and answers
"how much have I labelled?" cheaply enough to render on every keystroke. Owns the
dataset directory layout, the SQLite index over it, and the COCO export.

## Architecture

Decided at wave planning: **COCO JSON for interchange, native sidecar for everything
COCO cannot express.** COCO has no place for `unclear`, no notion of a box's
provenance, and no field for the prompt that produced it — all three are load-bearing
for this app, and inventing custom COCO keys would produce a file that claims to be
COCO but is not.

```
<data_dir>/datasets/<dataset_id>/
  dataset.json            native manifest — the source of truth
  annotations.coco.json   generated export (positive boxes only)
  images/                 copied images, when copy_images is on

<data_dir>/dinotraining.db   SQLite index over all datasets
```

SQLite is an *index*, not the truth: it makes counters and listings fast. A lost
database can be rebuilt from the `dataset.json` files. Every table write and the
manifest write happen in the same transaction, so the two cannot disagree.

## Data Model

All access goes through `db.get_connection()` — the single shared connection module
CLAUDE.md calls for. No module opens `sqlite3.connect` itself.

```sql
datasets(id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
         prompt TEXT, copy_images INTEGER NOT NULL DEFAULT 0)

images(id INTEGER PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES datasets(id)
         ON DELETE CASCADE,
       path TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
       annotated_at TEXT NOT NULL,
       UNIQUE(dataset_id, path))

boxes(id INTEGER PRIMARY KEY, image_id INTEGER NOT NULL REFERENCES images(id)
         ON DELETE CASCADE,
      label TEXT NOT NULL CHECK(label IN ('positive','negative','unclear')),
      provenance TEXT NOT NULL CHECK(provenance IN ('grounding-dino','hand-drawn')),
      prompt TEXT, score REAL,
      x REAL NOT NULL, y REAL NOT NULL, w REAL NOT NULL, h REAL NOT NULL)
```

Indexes on `images(dataset_id)` and `boxes(image_id)` — the counter query hits both.
`CHECK` constraints keep an invalid label out of the file even if a caller skips
validation; foreign keys are enforced with `PRAGMA foreign_keys=ON` on every connection.

Boxes are stored in **absolute pixel** coordinates, origin top-left, `x,y` = top-left
corner. Same convention as COCO, so the export is a copy rather than a conversion —
one convention in the system means no silent double-normalisation.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/datasets` | Create. Body: `name`, optional `prompt`, `copy_images`. → `201` |
| `GET` | `/datasets` | List with counts |
| `GET` | `/datasets/{id}` | Detail with counts. `404` unknown |
| `DELETE` | `/datasets/{id}` | Remove rows and directory |
| `PUT` | `/datasets/{id}/images` | Upsert one image's boxes (idempotent). `404` unknown dataset, `400` invalid box |
| `GET` | `/datasets/{id}/counts` | `{images, positive, negative, unclear, boxes}` |
| `POST` | `/datasets/{id}/export/coco` | Write `annotations.coco.json`, return path + counts |

`PUT` (not `POST`) on images is deliberate: re-reviewing an image replaces its boxes
rather than appending. Appending is how you end up with an image carrying three
contradictory sets of labels.

## Business Rules

- **Replace, never append.** `replace_image_boxes` deletes the image's existing boxes
  and inserts the new set inside one transaction.
- **Box geometry is validated:** `w > 0`, `h > 0`, and the box must lie within the
  image bounds. A zero-area or out-of-frame box is a `400`, not a stored row.
- **`unclear` is a first-class label**, never silently mapped to negative. It exists so
  the user is not forced into a bad binary decision, and Wave 2 can choose to exclude it.
- **COCO export contains positive boxes only** — that is what "an object is here" means
  to a downstream consumer. Negatives and unclears stay in the native manifest, where
  the trainer can use them as hard negatives.
- **Every path is confined** under the data dir with `ensure_within` before any write
  or delete. Dataset ids are generated, never caller-supplied.
- **Counts come from SQL aggregates**, not by loading annotations into memory.

## Data Flow

`counts` — computed by an aggregate query in `store.counts()` → transported as
`DatasetCounts` on `GET /datasets/{id}/counts` → consumed by the Wave 1 counter UI in
`annotation-workflow`. The same query backs the list endpoint, so the number on the
list and the number in the header cannot drift.

## Dependencies

- `01-app-shell` — `get_settings()` for `data_dir`, the error envelope, `apiFetch`.
- `02-model-manager` — reuses `ensure_within()` rather than re-deriving confinement.

## Security

**Untrusted input:** `dataset_id`, and the image `path` a client submits.

- Dataset ids are server-generated (`uuid4` hex). A caller-supplied id is only ever used
  as a lookup key, and an unknown one is a `404` before any path is built.
- Image paths are recorded as given but **confined before any read or copy**. Nothing in
  this feature reads image bytes from a caller-supplied path outside the data dir unless
  the user explicitly picked that folder — that decision belongs to `annotation-workflow`.
- Deleting a dataset resolves the directory through `ensure_within` and refuses the data
  root itself, so a malformed id cannot escalate into deleting the user's library.
- SQL is parameterised throughout; no query is assembled by string interpolation.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
