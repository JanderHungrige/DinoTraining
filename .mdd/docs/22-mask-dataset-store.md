---
id: 22-mask-dataset-store
title: Mask Dataset Store — COCO RLE Masks, Widened Provenance & Schema Migrations
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [03-dataset-store]
relates: [06-annotation-workflow, 16-inference-engine]
source_files:
  - backend/app/datasets/schema.py
  - backend/app/datasets/migrations.py
  - backend/app/datasets/rle.py
  - backend/app/datasets/masks.py
  - backend/app/datasets/images.py
  - backend/app/datasets/models.py
  - backend/app/datasets/db.py
  - backend/app/datasets/coco.py
  - backend/app/api/v1/datasets.py
routes:
  - PUT /api/v1/datasets/{dataset_id}/images/masks
models:
  - masks
  - boxes
test_files:
  - backend/tests/test_migrations.py
  - backend/tests/migration_testkit.py
  - backend/tests/test_rle.py
  - backend/tests/test_masks.py
  - backend/tests/test_datasets_masks_api.py
  - backend/tests/datasets_api_testkit.py
  - backend/tests/test_datasets_api.py
data_flow: writes-existing
last_synced: 2026-08-19
status: complete
phase: all
mdd_version: 11
tags: [sqlite, migrations, coco-rle, segmentation, masks, provenance, dataset-store]
path: Platform/Datasets
integration_contracts:
  - function: run_migrations(connection)
    when: on every connection open, before any query
    note: any future schema change must be added as a migration step, never by editing schema.py alone
satisfies_contracts: []
known_issues: []
security_read_sites: []
---

# 22 — Mask Dataset Store

## Purpose

Wave 4 needs segmentation masks to be storable, so SAM 3's proposals can become training
targets and segmentation finally becomes trainable in-app. `03-dataset-store` stores boxes
only. This feature adds mask storage as COCO RLE, widens annotation provenance to cover the
two new producers (`expert-head`, `sam3`), and — because it is the first change in the
project's history that **modifies** an existing table rather than adding one — introduces the
schema migration runner the store never had.

## The migration problem this feature exists to fix

`db.py` applies its schema with `CREATE TABLE IF NOT EXISTS` via `executescript`. That is a
**no-op against a table that already exists**, so changing a column or a `CHECK` constraint
has no effect on any database that predates the change.

Wave 2 was unaffected: it only added `head_instances`, a new table, which `IF NOT EXISTS`
creates correctly. `backend/tests/test_head_instances.py:219` asserts exactly that and is
still true.

Wave 4 is different. It must widen:

```sql
provenance TEXT NOT NULL CHECK (provenance IN ('grounding-dino', 'hand-drawn'))
```

to also allow `expert-head` and `sam3`. Verified behaviour:

| Database | Result of inserting `provenance='expert-head'` |
|---|---|
| Fresh (what every test builds) | insert succeeds — **suite goes green** |
| Pre-existing (what the user has) | `IntegrityError: CHECK constraint failed` — **app 500s** |

This is the project's recurring bug shape: a test suite that cannot see the runtime it will
actually meet. `SCHEMA_VERSION = 2` existed in `db.py` but was **never read by anything** —
it documented an intention that was not implemented.

**A test that only builds a fresh database cannot catch this.** `test_migrations.py` must
construct a database at the *old* shape, run the migration, and then assert the new insert
succeeds — and must be confirmed to fail against the un-migrated code.

## Verifying a migration against a real database

Two traps, both hit while verifying this feature.

**1. The runner must be exercised in `get_connection`'s call order.** `get_connection`
applies `schema.py` and *then* calls `run_migrations`. The first version of the runner
decided whether to migrate by asking "does the `masks` table exist?" — which
`executescript(SCHEMA_SQL)` has *already made true* by the time the runner is consulted. It
therefore skipped the migration for every real install while all fifteen migration tests
stayed green, because they called `run_migrations` on a bare legacy connection. The fix is
that each step inspects the DDL SQLite actually stored (`sqlite_master.sql`) rather than any
proxy signal. `TestTheRealCallOrder` reproduces the production sequence and is the test that
catches this.

**2. Copying a WAL-mode database without its `-wal` file gives a stale snapshot.** The
database runs in WAL mode, so `cp dinotraining.db` alone reads only the last *checkpoint* —
which here was over a day old and disagreed with the live state in both directions (it showed
24 images that were no longer there, and none of the 3 installed heads that were). Copy
`dinotraining.db`, `-wal` and `-shm` together, or run `PRAGMA wal_checkpoint(TRUNCATE)`
first. A stale copy is still a valid *old-shape* database and so is fine for testing the
migration itself — but it is not evidence about what the user currently has, and reading it
as such looks exactly like data loss.

## Architecture

```
db.py           connection + PRAGMAs, delegates schema work
  └── schema.py       current DDL (the shape a fresh database is created at)
  └── migrations.py   PRAGMA user_version + ordered steps (the shape an old one is moved to)

store.py        box write path   (unchanged — already 286 lines, at the hook limit)
masks.py        mask write path  (new sibling, NOT an extension of store.py)
rle.py          COCO RLE encode / decode / bbox / area
```

`store.py` is deliberately not touched beyond its imports. It is at 286 of the 300-line
limit, and the mask path is a genuinely separate concern with its own table.

## Data Model

### `masks` (new)

Mirrors `boxes` field-for-field wherever the concept is the same, so one review UI and one
export path can serve both.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `image_id` | INTEGER NOT NULL | `REFERENCES images(id) ON DELETE CASCADE` |
| `label` | TEXT NOT NULL | `CHECK IN ('positive','negative','unclear')` — same three verdicts as boxes |
| `provenance` | TEXT NOT NULL | `CHECK IN ('grounding-dino','hand-drawn','expert-head','sam3')` |
| `prompt` | TEXT | the SAM 3 concept, or the originating box prompt |
| `score` | REAL | model confidence, nullable |
| `rle_counts` | TEXT NOT NULL | JSON array of run lengths, column-major (COCO uncompressed RLE) |
| `rle_height` | INTEGER NOT NULL | `CHECK > 0` — must equal the image height |
| `rle_width` | INTEGER NOT NULL | `CHECK > 0` — must equal the image width |
| `x`,`y`,`w`,`h` | REAL NOT NULL | the mask's bounding box, derived on write |

`x,y,w,h` are **derived and stored, not supplied**. Keeping them means listing, filtering and
overlay placement never decode an RLE, which is the difference between an O(1) query and
decoding every mask in a dataset to render a list.

### `boxes` (rebuilt)

Identical except the widened `provenance` CHECK. Rebuilt rather than altered because SQLite
cannot alter a constraint in place.

### Why uncompressed RLE

COCO permits `counts` as either a compressed byte string (what `pycocotools` emits) or a
plain list of run lengths. The list form is chosen because it needs **no new dependency**,
round-trips exactly, and is readable by any COCO consumer. `pycocotools`' compressed form
would be smaller but adds a C-extension dependency to an app that installs on three
platforms. Run-length encoding already gives the large win over a dense mask; the compressed
string is a second-order saving.

Column-major order and a leading zero-run are the COCO convention and are **not** optional —
a row-major encoding is silently wrong to every other reader.

## API Endpoints

### `PUT /api/v1/datasets/{dataset_id}/images/masks`

Upsert one image and **replace** its masks — the same replace-don't-append rule
`replace_image_boxes` follows, for the same reason: re-reviewing must not leave stale
verdicts behind.

- **Body:** `ImageMaskAnnotation` — `path`, `width`, `height`, `masks[]`, optional `prompt`
- **200:** `DatasetCounts` (now including `masks`)
- **404:** unknown `dataset_id`
- **422:** RLE size disagrees with the stated image size, or a decoded run overflows the frame

The `422` path matters: a mask whose RLE size does not match its image is an upstream bug,
and storing it would hide that bug — the same stance `ImageAnnotation` takes for boxes that
fall outside the frame.

## Business Rules

- **A mask's RLE size must equal its image's `(height, width)`.** Rejected as `ValueError` →
  422, never stored.
- **Run lengths must sum to exactly `height * width`.** A short or long RLE is corrupt.
- **Masks are replaced per image, not appended.**
- **Deleting an image or dataset cascades to masks** — guaranteed by `PRAGMA foreign_keys`,
  which `db.py` already sets on every connection.
- **`DatasetCounts.masks` counts mask rows**; `boxes` continues to count only box rows. They
  are separate tallies, never summed into one "annotations" number, because the trainer
  consumes them for different tasks.
- **COCO export emits `segmentation` for positive masks only** — same rule as boxes. A
  negative mask asserts "this is not the thing", which as a COCO annotation would teach a
  consumer the opposite.

## Migration Rules

- `PRAGMA user_version` is the single source of truth for schema version. `SCHEMA_VERSION`
  in `db.py` is replaced by `LATEST_VERSION` in `migrations.py` and is **read**, not just
  declared.
- **A fresh database** (no `datasets` table) is created from `schema.py` at the current shape
  and stamped straight to `LATEST_VERSION` — migrations are not replayed.
- **An existing database** at `user_version = 0` is a Wave 1/2 install. Its version is
  inferred from what tables exist, then steps run in order.
- **Every future schema change adds a migration step.** Editing `schema.py` alone is the bug
  this feature exists to prevent, and is called out in `integration_contracts`.
- Constraint changes use the SQLite table-rebuild dance: create new, copy, drop, rename,
  recreate indexes — with `foreign_keys` off for the duration, since it must be toggled
  outside a transaction.

## Data Flow

- **Mask in:** SAM 3 / expert head → `Mask` pydantic model (RLE validated) → `masks.py`
  derives bbox → SQLite row. Bbox is computed once on write, never on read.
- **Counts out:** SQL `GROUP BY label` over `masks`, joined to `images` — the same shape
  `store.counts` already uses for boxes. Never load rows to tally them.
- **COCO out:** `rle.py` decodes nothing; the stored `counts` list and `size` go straight into
  the COCO `segmentation` field, because that is already the COCO wire format.

## Dependencies

- `03-dataset-store` — owns `datasets`, `images`, `boxes`, the manifest and the COCO export
  this feature extends.

## Security

Accepts external input (an RLE from an API caller). Untrusted: `rle_counts` length and sum,
and the stated `width`/`height`. A malicious or buggy caller could send a counts list that
sums far beyond the frame, so the sum is validated against `height * width` **before** any
decode and before any allocation — the validation is arithmetic on the list, never a
materialised mask. Path handling is unchanged and still flows through
`03-dataset-store`'s `ensure_within`.

## Known Issues

- Segmentation **class** is carried as the free-text `prompt`, mirroring how boxes work.
  Whether the Wave 2 trainer should derive its class list from distinct prompts, or masks
  need an explicit class column, is unresolved — it is listed in the wave's Open Research
  and should be settled before feature 7 writes generated data at volume.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
